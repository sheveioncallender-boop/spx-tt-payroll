"""Read-only v1.8.8 audit. Runs actual addon method bodies with ORM boundary doubles.

Usage: python checks/audit_calculations.py /path/to/addon [--odoo-source /path/to/odoo19]
This is NOT an Odoo installation, transaction, ACL, UI or PDF integration test.
Expected results are independent fixtures, requirements or external observations.
FAIL identifies a mismatch; ERROR identifies an unusable harness case.
"""
import argparse
import ast
import calendar
import csv
import hashlib
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from types import SimpleNamespace as NS
import pytz
from dateutil.relativedelta import relativedelta
from lxml import etree

parser = argparse.ArgumentParser()
parser.add_argument('addon', type=Path)
parser.add_argument('--odoo-source', type=Path)
args = parser.parse_args()
ROOT = args.addon.resolve()
OUT = Path(__file__).resolve().parent
results = []

def check(name, expected, operation, group='logic'):
    try:
        actual = operation()
        ok = actual == expected
        results.append(dict(name=name, group=group, status='PASS' if ok else 'FAIL',
                            expected=expected, actual=actual))
    except Exception as exc:
        results.append(dict(name=name, group=group, status='ERROR',
                            expected=expected, error=f'{type(exc).__name__}: {exc}'))

def money(value):
    return float(Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

class UserError(Exception):
    pass

class Records(list):
    def filtered(self, criterion):
        predicate = (lambda r: getattr(r, criterion)) if isinstance(criterion, str) else criterion
        return Records(r for r in self if predicate(r))
    def mapped(self, key):
        return [getattr(r, key) for r in self]
    def sorted(self, key=None):
        return Records(sorted(self, key=key))
    def __sub__(self, other):
        return Records(r for r in self if r not in other)
    def __getitem__(self, index):
        value = super().__getitem__(index)
        return Records(value) if isinstance(index, slice) else value
    def unlink(self):
        for r in self:
            r.deleted = True

class Base(NS):
    def ensure_one(self): pass
    def __iter__(self): return iter([self])
    def with_context(self, **values):
        self.env = NS(context={**getattr(self.env, 'context', {}), **values})
        return self
    def write(self, values):
        self.__dict__.update(values)
        return True
    def create(self, values): return Records(Base(**v) for v in values)

scope = dict(models=NS(Model=Base, TransientModel=Base), UserError=UserError,
             ValidationError=UserError, date=date, datetime=datetime, time=time,
             timedelta=timedelta, relativedelta=relativedelta, pytz=pytz,
             _=lambda value: value, fields=NS(Date=NS(context_today=lambda r: date(2026, 1, 31))))

exec((ROOT/'models/calculation_math.py').read_text(), scope)
exec((ROOT/'models/calculation_security.py').read_text(), scope)

def load(filename):
    source = ast.parse((ROOT / filename).read_text())
    for node in source.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets):
            exec(compile(ast.Module(body=[node], type_ignores=[]), filename, 'exec'), scope)
        elif isinstance(node, ast.ClassDef):
            node.body = [m for m in node.body if isinstance(m, ast.FunctionDef)]
            for m in node.body: m.decorator_list = []
            exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), filename, 'exec'), scope)

for filename in ['models/payroll_run_employee.py', 'models/payroll_run.py', 'models/payroll_run_item.py']:
    load(filename)
Employee = scope['TTPayrollRunEmployee']
Run = scope['TTPayrollRun']
Item = scope['TTPayrollRunItem']

def profile(**kw):
    values = dict(resident=True, paye_exempt=False, personal_allowance_override=0,
                  approved_pension_annuity_annual=0, approved_other_deductions_annual=0,
                  approved_tax_credits_annual=0, retirement_pension_recipient=False,
                  pension_only_income=False, td1_approved=True, td1_effective_date=False,
                  td1_expiry_date=False, opening_ytd_year=2026, opening_period_count=0,
                  opening_taxable_earnings=0, opening_paye=0, opening_employee_nis=0,
                  opening_health_surcharge=0, opening_income=0, opening_additions=0,
                  opening_gross=0, opening_other_deductions=0, opening_loans=0, opening_net=0)
    values.update(kw)
    return NS(**values)

def make_line(gross=9500, cycle='MONTHLY', weeks=4, prof=None, **kw):
    pay_item = Base(one_off=False, amount=gross, category='earning', exclude_from_paye=False,
                    nis_applicable=True, statutory_code='none', source='salary',
                    show_on_payslip=True, payslip_section='wage', sequence=1, id=1)
    statutory = [Base(amount=0, category='employer' if code == 'employer_nis' else 'deduction',
                      statutory_code=code, source='statutory', show_on_payslip=True,
                      payslip_section='employer' if code == 'employer_nis' else 'tax',
                      reference=False, sequence=10, id=i+2)
                 for i, code in enumerate(['paye','employee_nis','employer_nis','health_surcharge'])]
    for item in statutory:
        item.write = lambda vals, item=item: item.__dict__.update(vals, amount=vals['manual_amount'])
    run = Run(pay_frequency_id=NS(code=cycle), monday_count=weeks, period_week_count=weeks,
              payment_date=date(2026,1,31), date_start=date(2026,1,1), date_end=date(2026,1,31),
              payroll_year=2026)
    p = prof or profile()
    values = dict(id=1, run_id=run, run_state='draft', pay_frequency_id=NS(code=cycle),
                  employee_id=NS(id=1,birthday=date(1990,1,1),resource_calendar_id=True), company_id=NS(id=1),
                  nis_exempt=False, health_surcharge_exempt=False,
                  currency_id=NS(round=money), item_line_ids=Records([pay_item]+statutory),
                  _get_statutory_profile=lambda:p, pay_basis='salary', scheduled_hours=160,
                  period_salary=9500, payable_hours=160, hourly_rate=50,
                  normal_hours_per_week=40, regular_hours=160, paid_leave_hours=0,
                  incomplete_attendance_count=0, pending_overtime_hours=0,
                  pending_time_off_count=0, time_off_attendance_overlap_hours=0, attendance_record_count=1,
                  unpaid_leave_hours=0, public_holiday_hours=0, attendance_adjustment_hours=0,
                  env=NS(context={}), search=lambda domain:Records(),
                  review_state='pending', display_status='ready')
    values.update(kw)
    return Employee(**values)

def calculate(line):
    line._calculate_statutory_items()
    line._compute_totals()
    totals = {item.statutory_code: item.amount for item in line.item_line_ids if item.statutory_code != 'none'}
    totals['net'] = money(line.net_pay)
    return totals

# Static package checks; do not confuse schema validity with successful installation.
manifest = ast.literal_eval((ROOT/'__manifest__.py').read_text())
check('Baseline version', '19.0.1.8.8', lambda:manifest['version'], 'package')
check('Accounting and Enterprise payroll remain optional', ['hr','hr_attendance','hr_holidays','mail'], lambda:manifest['depends'], 'package')
for f in sorted(ROOT.rglob('*.py')):
    check(f'Python syntax: {f.relative_to(ROOT)}', True, lambda f=f: bool(compile(f.read_text(),str(f),'exec')), 'package')
for name in manifest['data'] + [p for paths in manifest['assets'].values() for p in paths]:
    relative = name.removeprefix('spx_tt_payroll/')
    check(f'Manifest file: {relative}', True, lambda relative=relative:(ROOT/relative).is_file(), 'package')
for f in sorted(ROOT.rglob('*.xml')):
    check(f'XML parse: {f.relative_to(ROOT)}', True, lambda f=f:etree.parse(str(f)) is not None, 'package')
if args.odoo_source:
    rng = etree.RelaxNG(etree.parse(str(args.odoo_source/'odoo/import_xml.rng')))
    list_rng = etree.RelaxNG(etree.parse(str(args.odoo_source/'odoo/addons/base/rng/list_view.rng')))
    for f in sorted(ROOT.rglob('*.xml')):
        tree = etree.parse(str(f))
        check(f'Odoo XML schema: {f.relative_to(ROOT)}', True, lambda tree=tree:rng.validate(tree), 'package')
        for i, element in enumerate(tree.xpath('//field[@name="arch"]/list')):
            check(f'Odoo list schema: {f.name} #{i+1}', True, lambda element=element:list_rng.validate(element), 'package')
    legacy = sorted(str(f.relative_to(ROOT)) for f in ROOT.rglob('*.py') if '_sql_constraints =' in f.read_text())
    check('Odoo 19 supported SQL constraint declarations', [], lambda:legacy, 'compatibility')

# Independent table fixture transcribed from NIBTT 05 January 2026 PDF.
official = [
 ('I',200,339.99,867,1472.99,14.6,29.2,2.2),('II',340,449.99,1473,1949.99,21.3,42.6,3.2),
 ('III',450,609.99,1950,2642.99,28.6,57.2,4.3),('IV',610,759.99,2643,3292.99,37,74,5.56),
 ('V',760,929.99,3293,4029.99,45.6,91.2,6.84),('VI',930,1119.99,4030,4852.99,55.4,110.8,8.32),
 ('VII',1120,1299.99,4853,5632.99,65.3,130.6,9.8),('VIII',1300,1489.99,5633,6456.99,75.3,150.6,11.3),
 ('IX',1490,1709.99,6457,7409.99,86.4,172.8,12.96),('X',1710,1909.99,7410,8276.99,97.7,195.4,14.66),
 ('XI',1910,2139.99,8277,9272.99,109.4,218.8,16.42),('XII',2140,2379.99,9273,10312.99,122,244,18.3),
 ('XIII',2380,2629.99,10313,11396.99,135.3,270.6,20.3),('XIV',2630,2919.99,11397,12652.99,149.9,299.8,22.49),
 ('XV',2920,3137.99,12653,13599.99,163.6,327.2,24.55),('XVI',3138,None,13600,None,169.5,339,25.43)]
check('All 16 NIBTT rows including employer/Class Z amounts', official, lambda:list(scope['NIS_2026_CLASSES']), 'NIS')
for row in official:
    for cycle,low,high in [('WEEKLY',row[1],row[2]),('MONTHLY',row[3],row[4])]:
        for amount in [low, high if high is not None else 1000000]:
            check(f'NIS {cycle} boundary {amount}', row[0], lambda cycle=cycle,amount=amount:make_line(cycle=cycle)._find_nis_class(amount)['name'], 'NIS')
check('Fortnightly 679.99 has a valid NIS class', True, lambda:bool(make_line(cycle='FORTNIGHTLY')._find_nis_class(679.99)), 'NIS')
for weeks,expected in [(4,(488,976,33)),(5,(610,1220,41.25))]:
    check(f'9500 monthly {weeks} Mondays', expected, lambda weeks=weeks:tuple(calculate(make_line(weeks=weeks))[k] for k in ['employee_nis','employer_nis','health_surcharge']), 'NIS')

# TT Paysheet browser observations: first pay 2026, resident, no TD1 or prior pay.
benchmarks = [
 ('MONTHLY',5000,0,261.2,33,4705.8),('MONTHLY',7500,0,390.8,33,7076.2),
 ('MONTHLY',9500,407.48,488,33,8571.52),('MONTHLY',12000,1011.33,599.6,33,10356.07),
 ('MONTHLY',15000,1746.46,678,33,12542.54),('MONTHLY',100000,23429.09,678,33,75859.91),
 ('WEEKLY',109,0,0,4.8,104.2),('WEEKLY',110,0,0,8.25,101.75),('WEEKLY',200,0,14.6,8.25,177.15),
 ('WEEKLY',2000,48.16,109.4,8.25,1834.19),('WEEKLY',4000,537.65,169.5,8.25,3284.6),
 ('WEEKLY',30000,7483.64,169.5,8.25,22338.61)]
comparison=[]
for cycle,gross,paye,nis,hs,net in benchmarks:
    actual=calculate(make_line(gross,cycle,1 if cycle=='WEEKLY' else 4))
    expected=dict(paye=paye,employee_nis=nis,health_surcharge=hs,net=net)
    comparison.append(dict(cycle=cycle,gross=gross,expected=expected,actual=actual))
    for key,value in expected.items():
        check(f'TT Paysheet {cycle} {gross}: {key}', value, lambda key=key:actual[key], 'calculator')

for gross,cycle,weeks,hs in [(0,'MONTHLY',4,0),(469.99,'MONTHLY',4,19.2),(470,'MONTHLY',4,33),
                            (109,'WEEKLY',1,4.8),(109.01,'WEEKLY',1,8.25)]:
    check(f'Health Surcharge boundary {cycle} {gross}', hs,
          lambda gross=gross,cycle=cycle,weeks=weeks:calculate(make_line(gross,cycle,weeks))['health_surcharge'],'statutory')
for birthday,employee_nis,employer_nis,hs in [(date(2010,2,1),0,73.2,0),
     (date(2010,1,31),488,976,33),(date(1966,1,31),488,976,0),(date(1961,1,31),0,73.2,0)]:
    check(f'Age boundary DOB {birthday}', (employee_nis,employer_nis,hs),
          lambda birthday=birthday:tuple(calculate(make_line(employee_id=NS(id=1,birthday=birthday)))[k]
           for k in ['employee_nis','employer_nis','health_surcharge']), 'statutory')
check('NIS exemption', (0,0), lambda:tuple(calculate(make_line(nis_exempt=True))[k] for k in ['employee_nis','employer_nis']), 'statutory')
check('PAYE exemption', 0, lambda:calculate(make_line(prof=profile(paye_exempt=True)))['paye'], 'statutory')
check('Nonresident gets no personal allowance', 2282.48, lambda:calculate(make_line(prof=profile(resident=False)))['paye'], 'statutory')
check('Pension plus NIS annual relief capped at 60000', 625, lambda:calculate(make_line(15000,prof=profile(approved_pension_annuity_annual=100000)))['paye'], 'statutory')
check('Tax credits floor PAYE at zero', 0, lambda:calculate(make_line(prof=profile(approved_tax_credits_annual=100000)))['paye'], 'statutory')

for hours,expected in [(0,0),(140,8312.5),(160,9500),(200,9500),(-8,0),(1,59.38)]:
    check(f'Salary 9500/160 payable {hours}',expected,lambda hours=hours:make_line(payable_hours=hours)._primary_earning_amount(),'wages')
for hours,expected in [(0,0),(140,7000),(180,9000),(-8,0)]:
    check(f'Hourly 50 payable {hours}',expected,lambda hours=hours:make_line(pay_basis='hourly',payable_hours=hours)._primary_earning_amount(),'wages')
for cycle,hours,salary in [('MONTHLY',160,9500),('WEEKLY',40,9500*12/52),('FORTNIGHTLY',80,9500*12/26),('SEMI_MONTHLY',80,4750)]:
    line=make_line(cycle=cycle)
    check(f'{cycle} expected hours',hours,lambda line=line:line._payroll_expected_hours(176),'wages')
    check(f'{cycle} salary conversion',money(salary),lambda line=line:money(line._period_salary_from_monthly(9500,line.run_id)),'wages')
for method,values,expected in [('manual',dict(manual_amount=900),900),('hours',dict(rate=50,quantity=8,factor=1.5),600),
                              ('fixed',dict(rate=100,quantity=2,factor=1),200),('percentage',dict(base_amount=9500,percentage=5,quantity=1,factor=1),475)]:
    item=Item(calculation_method=method,**values)
    def compute_item(item=item):
        item._compute_amount(); return item.amount
    check(f'Item amount: {method}',expected,compute_item,'wages')

def payable(**kw):
    line=make_line(**kw); line._recalculate_payable_hours()
    return (line.payable_hours,line.missing_hours,line.unpaid_hours)
check('Paid leave adds 8 to 132 attendance hours',(140,20,20),lambda:payable(regular_hours=132,paid_leave_hours=8),'attendance')
check('Unpaid leave explained shortage is not deducted twice',(152,0,8),lambda:payable(regular_hours=152,unpaid_leave_hours=8),'attendance')
check('Manual negative hours cannot make negative payable',(0,160,160),lambda:payable(regular_hours=4,attendance_adjustment_hours=-8),'attendance')
check('Salary payable capped at expected hours',(160,0,0),lambda:payable(regular_hours=180),'attendance')
check('Hourly payable not capped',(180,0,0),lambda:payable(pay_basis='hourly',regular_hours=180),'attendance')
attendance=Records([NS(check_in=datetime(2026,1,5,8),check_out=datetime(2026,1,5,16),
                       _get_worked_hours_in_range=lambda start,end:(end-start).total_seconds()/3600),
                    NS(check_in=datetime(2026,1,6,8),check_out=False)])
check('Completed attendance overlap only',4,lambda:make_line()._attendance_overlap_hours(attendance,datetime(2026,1,5,12),datetime(2026,1,5,20)),'attendance')

# Exercise Time Off aggregation using fixed calendar boundary answers.
def collect_leave(state='validate',unpaid=False,overlap=0,holiday=0):
    leave=NS(id=9,date_from=datetime(2026,1,5,8),date_to=datetime(2026,1,5,16),state=state,
             holiday_status_id=NS(unpaid=unpaid,id=2))
    model=NS(sudo=lambda:NS(search=lambda *a,**kw:Records([leave])))
    line=make_line(env={'hr.leave':model}, employee_id=NS(id=1,resource_calendar_id=NS(get_work_hours_count=lambda *a,**kw:8)))
    line._public_holiday_hours_in_range=lambda *a:holiday
    line._attendance_overlap_hours=lambda *a:overlap
    total=line._collect_time_off_snapshot(datetime(2026,1,1),datetime(2026,2,1),
          datetime(2026,1,1,tzinfo=pytz.UTC),datetime(2026,2,1,tzinfo=pytz.UTC),Records())
    return [total[k] for k in ['paid','unpaid','pending_hours','attendance_overlap','unpaid_overlap']]
check('Approved paid leave', [8,0,0,0,0],lambda:collect_leave(),'leave')
check('Approved unpaid leave', [0,8,0,0,0],lambda:collect_leave(unpaid=True),'leave')
check('Pending leave not paid', [0,0,8,0,0],lambda:collect_leave(state='confirm'),'leave')
check('Partially approved leave not paid', [0,0,8,0,0],lambda:collect_leave(state='validate1'),'leave')
check('Paid leave attendance overlap removed', [4,0,0,4,0],lambda:collect_leave(overlap=4),'leave')
check('Unpaid attendance overlap identified', [0,8,0,4,4],lambda:collect_leave(unpaid=True,overlap=4),'leave')
check('Public holiday not also counted as paid leave', [0,0,0,0,0],lambda:collect_leave(holiday=8),'leave')

def addition_test(exclude):
    line=make_line()
    line.item_line_ids.append(Base(one_off=False,amount=250,category='earning',exclude_from_paye=exclude,nis_applicable=True,statutory_code='none'))
    val=calculate(line)
    return [line.gross_pay,line.taxable_earnings,val['employee_nis'],val['health_surcharge']]
check('Addition taxable by default',[9750,9750,488,33],lambda:addition_test(False),'totals')
check('PAYE exclusion leaves gross/NIS/HS intact',[9750,9500,488,33],lambda:addition_test(True),'totals')
def run_totals():
    lines=Records([NS(gross_pay=9500,total_deductions=935.6,net_pay=8564.4,employer_contribution_total=976,
                     review_state=state,display_status=state) for state in ['reviewed','on_hold','excluded']])
    run=Run(employee_line_ids=lines);run._compute_run_totals()
    return [run.employee_count,run.payable_employee_count,run.gross_pay,run.net_pay,run.employer_contributions]
check('Run totals exclude held/excluded',[3,1,9500,8564.4,976],run_totals,'totals')
for month in range(1,13):
    last=calendar.monthrange(2026,month)[1]
    run=Run(date_start=date(2026,month,1),date_end=date(2026,month,last),payment_date=date(2026,month,last))
    expected=sum(1 for day in range(1,last+1) if date(2026,month,day).weekday()==0)
    def count(run=run):run._compute_period_information();return run.monday_count
    check(f'2026-{month:02d} contribution Mondays',expected,count,'calendar')

# Reproductions of missing safeguards in the CURRENT baseline, not Phase 6 tests.
def rejected(action):
    try: action();return False
    except UserError:return True
for state in ['approved','paid','cancelled']:
    check(f'Normal employee edit blocked: {state}',True,lambda state=state:rejected(lambda:make_line(run_state=state).write({'salary_amount':1})),'protection')
    check(f'Normal item edit blocked: {state}',True,lambda state=state:rejected(lambda:Item(run_state=state).write({'manual_amount':1})),'protection')
check('Hours direct edit without wizard blocked',True,lambda:rejected(lambda:make_line().write({'attendance_adjustment_hours':1})),'protection')
check('Forged internal context must not bypass hours audit',True,lambda:rejected(lambda:make_line(env=NS(context={'tt_payroll_internal_write':True})).write({'attendance_adjustment_hours':1})),'protection')
check('Forged locked-write context must not alter paid line',True,lambda:rejected(lambda:make_line(run_state='paid',env=NS(context={'tt_payroll_allow_locked_write':True})).write({'salary_amount':1})),'protection')
# The inherited protection layer is tested below; testing only the old base
# create/write would miss its guards.
load('models/payroll_integrity.py')
RunGuard=scope['PayrollRunIntegrity']
EmployeeGuard=scope['PayrollEmployeeIntegrity']
Change=scope['PayrollChange']
ItemGuard=scope['PayrollItemIntegrity']
for state in ['approved','paid','cancelled']:
    run=RunGuard(state=state,env=NS(context={}),_lock_calculation=lambda:None)
    check(f'Parent lock blocks {state}',True,lambda run=run:rejected(run._assert_open),'protection')
    check(f'Parent lock blocks payment date edit {state}',True,
          lambda run=run:rejected(lambda:run.write({'payment_date':date(2027,1,1)})),'protection')
for vals in [{'state':'approved'},{'gross_pay':1},{'net_pay':1}]:
    run=RunGuard(env=NS(context={}),_lock_calculation=lambda:None)
    check(f'Direct run write rejected {vals}',True,lambda run=run,vals=vals:rejected(lambda:run.write(vals)),'protection')
for method,args_ in [(Change.write,({},)),(Change.unlink,())]:
    check(f'History immutable {method.__name__}',True,lambda method=method,args_=args_:rejected(lambda:method(Base(),*args_)),'protection')
for vals in [{'payable_hours':100},{'locked_summary':{}},{'review_state':'reviewed'},{'employee_id':99}]:
    line=EmployeeGuard(run_id=NS(_assert_open=lambda:None),env=NS(context={}))
    check(f'Direct employee write rejected {vals}',True,lambda line=line,vals=vals:rejected(lambda:line.write(vals)),'protection')
# Verify mutation hooks explicitly rather than substituting a fake ORM recompute.
item_tree=ast.parse((ROOT/'models/payroll_integrity.py').read_text())
item_class=next(c for c in item_tree.body if isinstance(c,ast.ClassDef) and c.name=='PayrollItemIntegrity')
for method_name in ['create','write','unlink']:
    method=next(m for m in item_class.body if isinstance(m,ast.FunctionDef) and m.name==method_name)
    check(f'Item {method_name} triggers statutory refresh',True,
          lambda method=method:any(isinstance(n,ast.Attribute) and n.attr=='_after_change' for n in ast.walk(method)),'wiring')
check('TD1 unconfirmed deduction must not reduce PAYE',407.48,lambda:calculate(make_line(prof=profile(td1_approved=False,approved_other_deductions_annual=12000)))['paye'],'TD1')
check('Expired TD1 deduction must not reduce PAYE',407.48,lambda:calculate(make_line(prof=profile(td1_expiry_date=date(2025,12,31),approved_other_deductions_annual=12000)))['paye'],'TD1')
def ytd_domain():
    domains=[]
    line=make_line(search=lambda domain:domains.append(domain) or Records())
    line._get_ytd_values()
    return ('review_state','not in',['on_hold','excluded']) in domains[0]
check('Statutory YTD excludes held/excluded historical employees',True,ytd_domain,'YTD')
def ytd_immutable():
    line=EmployeeGuard(locked_summary={'ytd':{'net':8564.4}})
    return line._payslip_summary_values()['ytd']['net'] == 8564.4
check('Completed payslip reads saved YTD',True,ytd_immutable,'YTD')

summary={s:sum(r['status']==s for r in results) for s in ['PASS','FAIL','ERROR']}
payload=dict(baseline_version=manifest['version'],method='Actual source methods with ORM boundary doubles; no Odoo database',
             summary=summary,benchmarks=comparison,results=results,
             source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
                            for f in sorted(ROOT.rglob('*.py'))})
(OUT/'results.json').write_text(json.dumps(payload,indent=2,default=str)+'\n')
print(json.dumps(summary))
for r in results:
    if r['status']!='PASS':print(f"{r['status']} [{r['group']}] {r['name']}: {r.get('actual',r.get('error'))}")
raise SystemExit(2 if summary['ERROR'] else 1 if summary['FAIL'] else 0)
