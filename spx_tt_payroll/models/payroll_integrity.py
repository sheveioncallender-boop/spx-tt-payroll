"""Corrections to the existing payroll flow; no replacements for native HR apps."""
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .calculation_security import INTERNAL, WORKFLOW, LOCKED, internal, workflow


class PayrollChange(models.Model):
    _name = "spx.tt.payroll.change"
    _description = "Payroll Change History"
    _order = "changed_at desc, id desc"

    run_id = fields.Many2one("spx.tt.payroll.run", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="run_id.company_id", store=True, index=True)
    employee_name = fields.Char()
    description = fields.Char(required=True)
    details = fields.Json()
    changed_by = fields.Many2one("res.users", required=True, ondelete="restrict")
    changed_at = fields.Datetime(required=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not workflow(self):
            raise UserError(_("Payroll history is recorded automatically."))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("Payroll change history cannot be changed."))

    def unlink(self):
        raise UserError(_("Payroll change history cannot be deleted."))


class PayrollRunIntegrity(models.Model):
    _inherit = "spx.tt.payroll.run"

    change_ids = fields.One2many("spx.tt.payroll.change", "run_id", readonly=True)
    # Avoid live company currency changes relabelling an existing payroll.
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, depends=["company_id"])

    def _lock_calculation(self):
        if not self:
            return
        self.check_access("write")
        # Serialize payroll transactions in each company, including two runs
        # containing the same employee. Only payroll tables are touched.
        self.env.cr.execute("SELECT min(id) FROM spx_tt_payroll_run WHERE company_id IN %s GROUP BY company_id ORDER BY min(id)", [tuple(self.company_id.ids)])
        anchors = tuple(row[0] for row in self.env.cr.fetchall())
        if anchors:
            self.env.cr.execute("SELECT id FROM spx_tt_payroll_run WHERE id IN %s ORDER BY id FOR UPDATE", [anchors])
            self.env.cr.execute("UPDATE spx_tt_payroll_run SET write_date=write_date WHERE id IN %s", [anchors])
        self.env.cr.execute("SELECT id FROM spx_tt_payroll_run WHERE id IN %s ORDER BY id FOR UPDATE", [tuple(self.ids)])
        # Concurrent transactions on an older snapshot must retry, not approve
        # a child edit that committed after their original database snapshot.
        self.env.cr.execute("UPDATE spx_tt_payroll_run SET write_date=write_date WHERE id IN %s", [tuple(self.ids)])
        self.invalidate_recordset(["state"])

    def _assert_open(self):
        self._lock_calculation()
        if any(run.state in LOCKED for run in self):
            raise UserError(_("Approved, paid, or cancelled payroll is locked."))

    def _record_change(self, description, details=None, employee_name=False):
        self.ensure_one()
        self.env["spx.tt.payroll.change"].sudo().with_context(tt_payroll_workflow=WORKFLOW).create({
            "run_id": self.id, "employee_name": employee_name, "description": description,
            "details": json.loads(json.dumps(details or {}, default=str)),
            "changed_by": self.env.user.id, "changed_at": fields.Datetime.now(),
        })

    def _set_state(self, state):
        return self.with_context(tt_payroll_workflow=WORKFLOW).write({"state": state})

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("state", "draft") != "draft" for vals in vals_list):
            raise UserError(_("Create payroll in Draft and use the payroll actions."))
        if any(set(vals) & {"gross_pay", "net_pay", "total_deductions", "employer_contributions", "change_ids"} for vals in vals_list):
            raise UserError(_("Payroll totals and history are generated automatically."))
        return super().create([dict(vals, state="draft") for vals in vals_list])

    def write(self, vals):
        self._lock_calculation()
        chatter = {"message_follower_ids", "message_ids", "activity_ids"}
        if not workflow(self):
            if "state" in vals or set(vals) & {"gross_pay", "net_pay", "total_deductions", "employer_contributions", "currency_id"}:
                raise UserError(_("Use the payroll actions to change the payroll status or calculated values."))
            if set(vals) - chatter:
                self._assert_open()
        before = self.read(list(set(vals) - chatter)) if set(vals) - chatter else []
        result = super().write(vals)
        if before:
            for run in self:
                run._record_change(_("Payroll updated"), {"before": [v for v in before if v["id"] == run.id], "after": vals})
        if "payment_date" in vals:
            self.employee_line_ids._invalidate_review()
            self.employee_line_ids._calculate_statutory_items()
        return result

    def action_approve(self):
        self._assert_open()
        self._check_state({"under_review", "calculated"})
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can approve payroll."))
        for run in self:
            lines = run.employee_line_ids.filtered(lambda line: line.review_state not in ("on_hold", "excluded"))
            if not lines:
                raise UserError(_("There are no payable employees in this payroll."))
            # Existing deductions must still equal a fresh calculation. If not,
            # the transaction rolls back: staff must recalculate and review.
            previous = {line.id: [(i.id, i.amount) for i in line.item_line_ids] for line in lines}
            lines._calculate_statutory_items()
            for line in lines:
                if run.pay_frequency_id.code == "OFF_CYCLE":
                    raise UserError(_("Off-cycle statutory allocation is not validated in this build. Use a regular payroll for payment; keep off-cycle corrections in Draft."))
                later = self.env["spx.tt.payroll.run.employee"].search_count([
                    ("employee_id", "=", line.employee_id.id), ("company_id", "=", run.company_id.id),
                    ("run_id", "!=", run.id), ("run_id.state", "in", ["approved", "paid"]),
                    ("review_state", "not in", ["on_hold", "excluded"]),
                    ("run_id.payment_date", ">=", run.payment_date),
                ])
                overlap = self.env["spx.tt.payroll.run.employee"].search_count([
                    ("employee_id", "=", line.employee_id.id), ("company_id", "=", run.company_id.id),
                    ("run_id", "!=", run.id), ("run_id.state", "in", ["approved", "paid"]),
                    ("review_state", "not in", ["on_hold", "excluded"]),
                    ("run_id.date_start", "<=", run.date_end), ("run_id.date_end", ">=", run.date_start),
                ])
                if later or overlap:
                    raise UserError(_("%s already has an overlapping or later completed payroll. Do not pay these hours twice or change completed YTD history.") % line.employee_id.name)
                if previous[line.id] != [(i.id, i.amount) for i in line.item_line_ids]:
                    raise UserError(_("Payroll figures have changed. Recalculate and review before approval."))
                issues = line._get_attention_items()
                if issues:
                    raise UserError(_("%s: %s") % (line.employee_id.name, "; ".join(issue["title"] for issue in issues)))
                if not line.attendance_confirmed or line.net_pay < 0:
                    raise UserError(_("Confirm attendance and resolve negative net pay before approval."))
                if run.company_id.tt_payroll_require_review and line.review_state != "reviewed":
                    raise UserError(_("Mark every payable employee Reviewed before approval."))
            # Freeze before the parent moves to its existing Approved status.
            for line in lines:
                line.with_context(tt_payroll_workflow=WORKFLOW).write({
                    "locked_summary": line._payslip_summary_values(),
                    "locked_identity": line._payslip_identity(),
                })
        return self._set_state("approved")

    def action_mark_paid(self):
        self._lock_calculation()
        self._check_state({"approved"})
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can mark payroll as paid."))
        return self._set_state("paid")

    def action_reset_to_draft(self):
        self._assert_open()
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can reset payroll."))
        self.employee_line_ids.with_context(tt_payroll_workflow=WORKFLOW).write({"review_state": "pending"})
        return self._set_state("draft")

    def action_cancel(self):
        self._assert_open()
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can cancel payroll."))
        return self._set_state("cancelled")

    def unlink(self):
        if self.filtered(lambda run: run.state != "draft" or run.change_ids or run.employee_line_ids.hours_adjustment_ids):
            raise UserError(_("A payroll with history must be retained. Cancel an unfinished payroll instead."))
        return super().unlink()


class PayrollEmployeeIntegrity(models.Model):
    _inherit = "spx.tt.payroll.run.employee"

    locked_summary = fields.Json(readonly=True, copy=False)
    locked_identity = fields.Json(readonly=True, copy=False)

    def _payslip_identity(self):
        self.ensure_one()
        return self.locked_identity or dict(employee=self.employee_id.name, company=self.company_id.name,
            department=self.department_id.name or "", frequency=self.pay_frequency_id.name or "")

    def _payslip_summary_values(self):
        self.ensure_one()
        return self.locked_summary or super()._payslip_summary_values()

    def _get_payslip_report_values(self):
        values = super()._get_payslip_report_values()
        values["identity"] = self._payslip_identity()
        return values

    def _invalidate_review(self):
        reviewed = self.filtered(lambda line: line.review_state == "reviewed")
        if reviewed:
            reviewed.with_context(tt_payroll_workflow=WORKFLOW).write({"review_state": "pending"})

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        runs = self.env["spx.tt.payroll.run"].browse([vals.get("run_id") or self.env.context.get("default_run_id") for vals in vals_list])
        runs._assert_open()
        for vals in vals_list:
            if not internal(self):
                unexpected = set(vals) - {"run_id", "employee_id", "review_state", "notes", "hold_reason"}
                if unexpected:
                    raise UserError(_("Add an existing employee; payroll loads their profile and clocked hours automatically."))
            vals.setdefault("run_id", self.env.context.get("default_run_id"))
            vals.setdefault("employee_id", self.env.context.get("default_employee_id"))
            vals.update(locked_summary=False, locked_identity=False, attendance_adjustment_hours=0.0, item_line_ids=[])
            if vals.get("review_state") == "reviewed" or self.env.context.get("default_review_state") == "reviewed":
                raise UserError(_("Use Mark Reviewed after checking the calculation."))
        # Context defaults supplied by an RPC caller must not become trusted
        # generated wages, hours or statutory values inside the internal build.
        clean_context = {key: value for key, value in self.env.context.items() if not key.startswith("default_")}
        records = super(PayrollEmployeeIntegrity, self.with_context(clean_context, tt_payroll_internal_write=INTERNAL)).create(vals_list)
        for line in records:
            line.run_id._record_change(_("Employee added to payroll"), employee_name=line.employee_id.name)
        return records.with_env(self.env)

    def write(self, vals):
        self.run_id._assert_open()
        if not workflow(self):
            if set(vals) & {"locked_summary", "locked_identity", "gross_pay", "net_pay", "total_deductions", "employer_contribution_total", "taxable_earnings", "nis_insurable_earnings"}:
                raise UserError(_("Payroll totals and saved payslip values are calculated automatically."))
            if vals.get("review_state") == "reviewed":
                raise UserError(_("Use Mark Reviewed after checking the calculation."))
        if not internal(self) and not workflow(self):
            protected = {"run_id", "employee_id", "company_id", "currency_id", "salary_amount", "period_salary",
                "hourly_rate", "pay_basis", "payable_hours", "regular_hours", "scheduled_hours", "overtime_hours",
                "paid_leave_hours", "unpaid_leave_hours", "public_holiday_hours", "attendance_confirmed",
                "attendance_status", "attendance_record_count", "incomplete_attendance_count", "actual_worked_hours",
                "pending_overtime_hours", "pending_time_off_count", "time_off_attendance_overlap_hours",
                "nis_exempt", "health_surcharge_exempt", "effective_hourly_rate"}
            if set(vals) & protected:
                raise UserError(_("Refresh the employee or Attendance & Time Off, or use Adjust Payable Hours."))
        result = super().write(vals)
        if not workflow(self):
            if set(vals) - {"message_follower_ids", "message_ids", "activity_ids", "review_state"}:
                self._invalidate_review()
            if not internal(self):
                for line in self:
                    line.run_id._record_change(_("Employee payroll updated"), vals, line.employee_id.name)
        return result

    def action_mark_reviewed(self):
        self.run_id._assert_open()
        for line in self:
            if line.review_state in ("on_hold", "excluded"):
                raise UserError(_("Include this employee before marking the calculation Reviewed."))
            line._calculate_statutory_items()
            issues = line._get_attention_items()
            if issues:
                raise UserError(_("Resolve the items requiring attention before marking this employee Reviewed."))
            line.with_context(tt_payroll_workflow=WORKFLOW).write({"review_state": "reviewed"})
            line.run_id._record_change(_("Employee calculation reviewed"), {"gross": line.gross_pay,
                "deductions": line.total_deductions, "net": line.net_pay}, line.employee_id.name)
        return True

    def _calculate_statutory_items(self):
        self.run_id._assert_open()
        return super(PayrollEmployeeIntegrity, self.with_context(tt_payroll_internal_write=INTERNAL))._calculate_statutory_items()

    def _load_default_items(self):
        self.run_id._assert_open()
        return super(PayrollEmployeeIntegrity, self.with_context(tt_payroll_internal_write=INTERNAL))._load_default_items()

    def _rebuild_attendance_earnings(self):
        self.run_id._assert_open()
        self._invalidate_review()
        return super(PayrollEmployeeIntegrity, self.with_context(tt_payroll_internal_write=INTERNAL))._rebuild_attendance_earnings()

    def unlink(self):
        self.run_id._assert_open()
        if self.hours_adjustment_ids:
            raise UserError(_("This employee has adjustment history. Exclude them from the run instead of deleting."))
        for line in self:
            line.run_id._record_change(_("Employee removed from payroll"), employee_name=line.employee_id.name)
        return super().unlink()


class PayrollItemIntegrity(models.Model):
    _inherit = "spx.tt.payroll.run.item"

    def _after_change(self, employees):
        if not internal(self):
            employees._invalidate_review()
            employees._calculate_statutory_items()

    def _check_manual_items(self):
        if not internal(self) and self.filtered(lambda item: item.source != "manual" and item.source != "recurring"
                or item.statutory_code != "none" or item.pay_item_id.code in ("BASIC", "REGULAR_HOURS")):
            raise UserError(_("Wages and statutory deductions are generated by payroll. Use the payroll adjustment actions."))

    @api.model_create_multi
    def create(self, vals_list):
        parents = self.env["spx.tt.payroll.run.employee"].browse([
            vals.get("run_employee_id") or self.env.context.get("default_run_employee_id") for vals in vals_list])
        parents.run_id._assert_open()
        records = super().create(vals_list)
        records._check_manual_items()
        if not internal(self):
            for item in records:
                item.run_id._record_change(_("Payroll item added"), item.read(["description", "category", "amount", "one_off", "exclude_from_paye", "nis_applicable"])[0], item.employee_id.name)
        self._after_change(records.run_employee_id)
        return records

    def write(self, vals):
        self.run_id._assert_open()
        if "run_employee_id" in vals or "amount" in vals:
            raise UserError(_("Payroll items cannot be moved and totals cannot be overwritten."))
        if not internal(self) and self.filtered(lambda item: item.source in ("basic", "salary", "attendance", "statutory")):
            raise UserError(_("Wages and statutory deductions are automatic. Use Adjust Payable Hours or employee statutory settings."))
        before = self.read(list(vals)) if not internal(self) else []
        result = super().write(vals)
        self._check_manual_items()
        if before:
            for item in self:
                item.run_id._record_change(_("Payroll item changed"), {"before": [v for v in before if v["id"] == item.id], "after": vals}, item.employee_id.name)
        self._after_change(self.run_employee_id)
        return result

    def unlink(self):
        self.run_id._assert_open()
        parents = self.run_employee_id
        if not internal(self) and self.filtered(lambda item: item.source in ("basic", "salary", "attendance", "statutory")):
            raise UserError(_("Automatic wages and statutory lines cannot be removed."))
        if not internal(self):
            for item in self:
                item.run_id._record_change(_("Payroll item removed"), item.read(["description", "amount"])[0], item.employee_id.name)
        result = super().unlink()
        self._after_change(parents)
        return result


class PayrollTimeOffIntegrity(models.Model):
    _inherit = "spx.tt.payroll.time.off.snapshot"

    @api.model_create_multi
    def create(self, vals_list):
        if not internal(self):
            raise UserError(_("Refresh Attendance & Time Off to load a snapshot."))
        self.env["spx.tt.payroll.run.employee"].browse([v["run_employee_id"] for v in vals_list]).run_id._assert_open()
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("Payroll Time Off snapshots cannot be edited. Correct the request in Odoo Time Off, then refresh payroll."))

    def unlink(self):
        if not internal(self):
            raise UserError(_("Refresh Attendance & Time Off to replace a snapshot."))
        self.run_id._assert_open()
        return super().unlink()


class PayrollStatutoryIntegrity(models.Model):
    _inherit = "spx.tt.employee.statutory.profile"

    @api.model_create_multi
    def create(self, vals_list):
        profiles = super().create(vals_list)
        lines = self.env["spx.tt.payroll.run.employee"].search([
            ("employee_id", "in", profiles.employee_id.ids), ("run_id.state", "not in", LOCKED)])
        lines.run_id._assert_open()
        lines._invalidate_review()
        lines._calculate_statutory_items()
        lines._compute_issues_and_status()
        return profiles

    def unlink(self):
        lines = self.env["spx.tt.payroll.run.employee"].search([
            ("employee_id", "in", self.employee_id.ids), ("run_id.state", "not in", LOCKED)])
        lines.run_id._assert_open()
        result = super().unlink()
        lines._invalidate_review()
        lines._calculate_statutory_items()
        lines._compute_issues_and_status()
        return result

    def write(self, vals):
        lines = self.env["spx.tt.payroll.run.employee"].search([
            ("employee_id", "in", self.employee_id.ids), ("run_id.state", "not in", LOCKED)])
        lines.run_id._assert_open()
        result = super().write(vals)
        if set(vals) - {"notes"}:
            lines._invalidate_review()
            lines._calculate_statutory_items()
            lines._compute_issues_and_status()
            for line in lines:
                line.run_id._record_change(_("Statutory settings refreshed"), vals, line.employee_id.name)
        return result


class PayrollItemDefinitionIntegrity(models.Model):
    _inherit = "spx.tt.pay.item"

    def write(self, vals):
        if "code" in vals:
            changed = self.filtered(lambda item: item.code != vals["code"])
            items = self.env["spx.tt.payroll.run.item"].sudo().search([("pay_item_id", "in", changed.ids)])
            items.run_id._assert_open()
            items.run_employee_id._invalidate_review()
        return super().write(vals)
