# -*- coding: utf-8 -*-
"""data.json -> Excel workbook (data / summary / methodology)."""
import json, argparse, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule
from openpyxl.comments import Comment

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="data.json")
ap.add_argument("--out", default=None)
A = ap.parse_args()

PAY = json.load(open(A.data, encoding="utf-8"))
if PAY.get("verification"):
    print("Refusing to build: scan did not pass verification:")
    for f in PAY["verification"]: print("  !", f)
    sys.exit(2)

NM = "غير مذكور"
ASOF = PAY["asOf"]
OUT = A.out or f"Furas_Opportunities_{ASOF}.xlsx"
CITY_LABEL = {"الرياض":"الرياض","جدة":"جدة","مكه المكرمه":"مكة المكرمة","المدينه المنوره":"المدينة المنورة"}
ORDER = ["الرياض","جدة","مكه المكرمه","المدينه المنوره"]

def _s(v): return (str(v).strip() if v is not None else "")
rows, COORDS, DET = [], {}, {}
for r in PAY["records"]:
    ref = _s(r.get("OPPORTUNITYID"))
    amana, ent = _s(r.get("AMANA")), _s(r.get("ENTITIESNAME"))
    rows.append({"ref":ref,"title":_s(r.get("OPPORTUNITYDESCRIPTION")),"city":_s(r.get("CITYNAME")),
        "authType":"أمانة/بلدية" if amana else "جهة شريكة","authority":amana or ent,
        "baladya":_s(r.get("BALADYA")),"district":_s(r.get("DISTRICT")),"street":_s(r.get("STREET")),
        "durationDays":_s(r.get("DURATION") or 0),"areaM2":_s(r.get("TOTALSPACEINMETERS")),
        "rfpPriceSAR":_s(r.get("RFPPRICE")),"lastRfpSell":_s(r.get("LASTRFPSELLDATE"))[:10],
        "endDate":_s(r.get("ENDDATE"))[:10],"envelopesOpen":_s(r.get("ENVELOPESOPENDATE"))[:10],
        "status":_s(r.get("STATUS")),"activity":_s(r.get("ACTIVITYTYPE")),
        "subactivity":_s(r.get("SUBACTIVITYTYPE"))})
    if r.get("_lat") is not None: COORDS[ref] = (r["_lat"], r["_lon"])
    DET[ref] = {"atts": r.get("_docs") or []}

def doc(ref, kw):
    for a in DET.get(ref, {}).get("atts", []):
        if kw in a["name"]: return a["url"]
    return None

NATIONAL = PAY.get("nationalOpenInvestment") or 0

def num(v):
    try: return float(str(v).replace(',','').strip())
    except: return None

recs=[]
for r in rows:
    a=num(r['areaM2']); p=num(r['rfpPriceSAR']); env=r['envelopesOpen'].strip()
    recs.append({
        'ref':r['ref'].strip(),'title':r['title'].strip(),
        'city':r['city'].strip(),'cityLabel':CITY_LABEL[r['city'].strip()],
        'authType':r['authType'].strip(),'authority':r['authority'].strip() or NM,
        'baladya':r['baladya'].strip() or NM,'district':r['district'].strip() or NM,
        'street':r['street'].strip() or NM,
        'area': (a if a and a>0 else NM),
        'months': int(num(r['durationDays']) or 0),
        'years': round(int(num(r['durationDays']) or 0)/12,1),
        'lat': COORDS.get(r['ref'].strip(),(None,None))[0],
        'lon': COORDS.get(r['ref'].strip(),(None,None))[1],
        'kurasa': doc(r['ref'].strip(),'كراسة'),
        'aqd': doc(r['ref'].strip(),'مسودة'),
        'price': (p if p and p>0 else NM),
        'deadline':r['lastRfpSell'].strip(),
        'env': (NM if (not env or env.startswith('1970')) else env),
        'status':'معلنة','activity':r['activity'].strip() or NM,
        'sub':r['subactivity'].strip() or NM})
recs.sort(key=lambda x:(ORDER.index(x['city']),x['deadline'],x['ref']))

BLUE="1F6B4F"; HDR=PatternFill("solid",fgColor="1F6B4F"); ZEB=PatternFill("solid",fgColor="EFF3F2")
WHITE=Font(name="Arial",size=10,bold=True,color="FFFFFF")
BODY=Font(name="Arial",size=10); BOLD=Font(name="Arial",size=10,bold=True)
TH=Side(style="thin",color="DCE3E1"); BOX=Border(left=TH,right=TH,top=TH,bottom=TH)

wb=Workbook()

# ---------- Sheet 1: data ----------
ws=wb.active; ws.title="الفرص"; ws.sheet_view.rightToLeft=True
COLS=[("رقم الفرصة",19),("العنوان",62),("المدينة",15),("نوع جهة الطرح",14),("جهة الطرح",34),
      ("البلدية",24),("الحي",18),("الشارع",22),("المساحة (م²)",14),("مدة العقد (سنة)",13),
      ("مدة العقد (شهر)",13),("سعر الكراسة (ر.س)",15),("نهاية الفرصة",13),("الأيام المتبقية",13),
      ("فتح المظاريف",13),("الحالة",10),("النشاط",26),("النشاط الفرعي",24),
      ("خط العرض",12),("خط الطول",12),("الخريطة",11),("كراسة الشروط",13),("مسودة العقد",13),("صفحة الفرصة",13)]
for i,(h,w) in enumerate(COLS,1):
    c=ws.cell(1,i,h); c.font=WHITE; c.fill=HDR; c.border=BOX
    c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
    ws.column_dimensions[get_column_letter(i)].width=w
ws.row_dimensions[1].height=32

for ri,r in enumerate(recs,2):
    vals=[r['ref'],r['title'],r['cityLabel'],r['authType'],r['authority'],r['baladya'],
          r['district'],r['street'],r['area'],r['years'],r['months'],r['price'],r['deadline'],
          f'=IF(M{ri}="","",M{ri}-TODAY())', r['env'],r['status'],r['activity'],r['sub'],
          r['lat'],r['lon'],None,None,None,None]
    for ci,v in enumerate(vals,1):
        c=ws.cell(ri,ci,v); c.font=BODY; c.border=BOX
        c.alignment=Alignment(vertical="top",wrap_text=(ci in(2,5,6,17,18)))
        if ri%2==0: c.fill=ZEB
    ws.cell(ri,9).number_format='#,##0.00;;"—"'
    ws.cell(ri,10).number_format='0.#'
    ws.cell(ri,11).number_format='#,##0'
    for cc,url,lab in ((21, (f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lon']}" if r['lat'] is not None else None), "خريطة"),
                       (24, f"https://furas.momah.gov.sa/opportunity/{r['ref']}?type=Investment", "فتح")):
        cell=ws.cell(ri,cc)
        if url:
            cell.value=lab; cell.hyperlink=url
            cell.font=Font(name="Arial",size=10,color="1F6B4F",underline="single")
        else:
            cell.value="—"; cell.font=Font(name="Arial",size=10,color="9AA8A2")
        cell.alignment=Alignment(horizontal="center",vertical="top")
    for cc,present in ((22, r['kurasa']), (23, r['aqd'])):
        cell=ws.cell(ri,cc); cell.value="متوفرة" if present else "—"
        cell.font=Font(name="Arial",size=10,color=("1F6B4F" if present else "9AA8A2"))
        cell.alignment=Alignment(horizontal="center",vertical="top")
    ws.cell(ri,19).number_format='0.000000'; ws.cell(ri,20).number_format='0.000000'
    ws.cell(ri,12).number_format='#,##0;;"—"'
    ws.cell(ri,13).number_format='YYYY-MM-DD'
    ws.cell(ri,14).number_format='#,##0'
    ws.cell(ri,15).number_format='@'
    for cc in (1,9,11,12,13,14): ws.cell(ri,cc).alignment=Alignment(horizontal="right",vertical="top")

last=len(recs)+1
ws.auto_filter.ref=f"A1:X{last}"
ws.freeze_panes="A2"
ws.conditional_formatting.add(f"N2:N{last}",
    CellIsRule(operator="lessThanOrEqual",formula=["14"],
               fill=PatternFill("solid",fgColor="FBEBE0"),font=Font(name="Arial",size=10,bold=True,color="9C4A18")))
ws.cell(1,10).comment=Comment(
 "مدة العقد الفعلية. حقل DURATION في واجهة البيانات يُقاس بالأشهر.\n"
 "جرى التحقق بمطابقة السجلات الـ175 كافة مع بطاقة التفاصيل في البوابة\n"
 "(«… شهر مدة العقد») — تطابق 175 من 175 بدون أي اختلاف.\n"
 "24 شهراً = سنتان · 300 = 25 سنة · 600 = 50 سنة. الأكثر شيوعاً: 25 سنة (62 فرصة).", "Claude", width=430, height=110)
ws.cell(1,22).comment=Comment(
 "«متوفرة» تعني أن الكراسة مدرجة في تبويب المرفقات بصفحة الفرصة.\n"
 "لم تُدرج روابط تحميل مباشرة: اختبار عيّنة في متصفح حقيقي أظهر أن بعض روابط\n"
 "المرفقات تعمل وبعضها يعيد التوجيه إلى صفحة القائمة — أرشيف المرفقات لدى\n"
 "البوابة غير مكتمل. استخدم عمود «صفحة الفرصة» للتحميل من المصدر.","Claude",width=430,height=100)
ws.cell(1,12).comment=Comment(
 "سعر الكراسة فقط (رسم شراء كراسة الشروط والمواصفات).\n"
 "الإيجار السنوي غير منشور: ANNUALVALUE و MINIMUMGURANTEE فارغان في جميع السجلات.","Claude",width=380,height=80)

# ---------- Sheet 2: summary (real formulas) ----------
s=wb.create_sheet("الملخص"); s.sheet_view.rightToLeft=True
s.column_dimensions['A'].width=26
for col in 'BCDE': s.column_dimensions[col].width=15
t=s.cell(1,1,"ملخص الفرص الاستثمارية طويلة الأجل — المدن الأربع")
t.font=Font(name="Arial",size=13,bold=True,color=BLUE)
s.cell(2,1,f"لقطة بتاريخ {ASOF} · المصدر: بوابة فرص (InvestmentP)").font=Font(name="Arial",size=9,italic=True)

hdr=["المدينة","الإجمالي","أمانة/بلدية","جهة شريكة","تنتهي ≤ 14 يوم"]
for i,h in enumerate(hdr,1):
    c=s.cell(4,i,h); c.font=WHITE; c.fill=HDR; c.border=BOX
    c.alignment=Alignment(horizontal="center",vertical="center")

D=f"الفرص!$C$2:$C${last}"; A=f"الفرص!$D$2:$D${last}"; N=f"الفرص!$N$2:$N${last}"
for i,c in enumerate(ORDER,5):
    lbl=CITY_LABEL[c]
    s.cell(i,1,lbl).font=BODY
    s.cell(i,2,f'=COUNTIF({D},A{i})').font=BODY
    s.cell(i,3,f'=COUNTIFS({D},A{i},{A},"أمانة/بلدية")').font=BODY
    s.cell(i,4,f'=COUNTIFS({D},A{i},{A},"جهة شريكة")').font=BODY
    s.cell(i,5,f'=COUNTIFS({D},A{i},{N},"<=14",{N},">=0")').font=BODY
    for ci in range(1,6): s.cell(i,ci).border=BOX

tr=5+len(ORDER)
s.cell(tr,1,"الإجمالي").font=BOLD
for ci,L in [(2,'B'),(3,'C'),(4,'D'),(5,'E')]:
    c=s.cell(tr,ci,f'=SUM({L}5:{L}{tr-1})'); c.font=BOLD; c.fill=ZEB
for ci in range(1,6): s.cell(tr,ci).border=BOX

s.cell(tr+2,1,"تحقق من السلامة").font=Font(name="Arial",size=11,bold=True,color=BLUE)
checks=[("عدد السجلات",f'=COUNTA(الفرص!$A$2:$A${last})'),
        ("سجلات بدون رقم فرصة",f'=COUNTBLANK(الفرص!$A$2:$A${last})'),
        ("المساحة: غير مذكور",f'=COUNTIF(الفرص!$I$2:$I${last},"{NM}")'),
        ("سعر الكراسة: غير مذكور",f'=COUNTIF(الفرص!$L$2:$L${last},"{NM}")'),
        ("فتح المظاريف: غير مذكور",f'=COUNTIF(الفرص!$O$2:$O${last},"{NM}")'),
        ("متوسط مدة العقد (سنة)",f'=ROUND(AVERAGE(الفرص!$J$2:$J${last}),1)'),
        ("عقود 25 سنة فأكثر",f'=COUNTIF(الفرص!$J$2:$J${last},">=25")'),
        ("لديها كراسة",f'=COUNTIF(الفرص!$V$2:$V${last},"متوفرة")'),
        ("لديها إحداثيات",f'=COUNT(الفرص!$S$2:$S${last})')]
for i,(k,f) in enumerate(checks,tr+3):
    s.cell(i,1,k).font=BODY; s.cell(i,2,f).font=BODY
    s.cell(i,1).border=BOX; s.cell(i,2).border=BOX

s.cell(tr+14,1,"السياق الوطني").font=Font(name="Arial",size=11,bold=True,color=BLUE)
ctx=[("الفرص طويلة الأجل المفتوحة وطنياً",NATIONAL or "لم يُقَس"),
     ("نصيب المدن الأربع",(f'=B{tr}/B{tr+15}' if NATIONAL else "—"))]
for i,(k,v) in enumerate(ctx,tr+15):
    s.cell(i,1,k).font=BODY; c=s.cell(i,2,v); c.font=BODY
    if isinstance(v,str) and v.startswith('='): c.number_format='0.0%'
    else: c.number_format='#,##0'
    s.cell(i,1).border=BOX; c.border=BOX

# ---------- Sheet 3: methodology ----------
m=wb.create_sheet("المنهجية"); m.sheet_view.rightToLeft=True
m.column_dimensions['A'].width=112
LINES=[("عنوان","المنهجية والقيود — مسح بوابة فرص"),
 ("h","النطاق والتصفية"),
 ("p","النوع: الفرص طويلة الأجل فقط (OPPORTUNITYTYPE = 'Investment'). استُثنيت TemporaryRental (التأجير المؤقت) و DirectRental بالكامل."),
 ("p","الحالة: OPPORTUNITYACTIVESTATUS = 'Announced' مع LASTRFPSELLDATE ≥ تاريخ اللقطة — أي أن كراسة الشروط لا تزال قابلة للشراء."),
 ("p","جهة الطرح: الأمانات والبلديات أو الجهات الشريكة — بناءً على توجيه الرئيس التنفيذي. الاكتفاء بالأمانات وحدها يُسقط 57 فرصة من 175، بما فيها فرص مكة المكرمة كافة (29)."),
 ("p","المدينة: المطابقة على اسم المدينة بعد تطبيع الحروف (ة/ه، أ/إ/آ/ا، ى/ي). البوابة تخزّن «مكه المكرمه» و«المدينه المنوره» بالهاء؛ البحث بالإملاء المعياري يعيد صفر نتيجة."),
 ("h","قيد جوهري: مدة العقد غير منشورة"),
 ("p","الحقول CONTRACTTERM و CONTRACTTERMVALUE و CONTRACTTERMWEIGHT و MODEL فارغة في جميع السجلات الـ175. لذلك تُعرض مدة العقد على أنها «غير مذكور»."),
 ("p","حقل DURATION (عمود «مدة الطرح») ليس مدة العقد: قيمه محصورة في أرقام إدارية ثابتة (24/36/60/84/120/180/240/300/600 يوم) ولا تساوي الفرق بين تاريخي البداية والنهاية — تطابقت في 4 سجلات فقط من 175."),
 ("p","لا يجوز استخدام «مدة الطرح» كمدة إيجار أو تعاقد في أي قرار. المدة التعاقدية الفعلية في كراسة الشروط والمواصفات."),
 ("h","قيد جوهري: الإيجار السنوي غير منشور"),
 ("p","ANNUALVALUE و MINIMUMGURANTEE و REVENUESHARINGPERCENTAGE فارغة في جميع السجلات. العمود «سعر الكراسة» هو رسم شراء الكراسة فقط وليس قيمة الإيجار."),
 ("p","نتيجة ذلك: لا يمكن الإجابة على سؤال «هل تستحق هذه الفرصة التقدم؟» من هذا الملف وحده — يلزم الرجوع إلى الكراسة."),
 ("h","القيم غير المذكورة"),
 ("p","المساحة صفر (8 سجلات) وسعر الكراسة صفر (17 سجلاً) وتاريخ فتح المظاريف الصفري 1970-01-01 (48 سجلاً) تُعرض جميعها «غير مذكور». لم تُقدَّر أي قيمة."),
 ("h","الوصول"),
 ("p","تم التحقق في 27 أغسطس 2026: البوابة وتطبيق الخريطة وواجهة البيانات تستجيب جميعها بدون تسجيل دخول وبدون نفاذ. لم يُنقر أي عنصر مصادقة."),
 ("h","المصدر"),
 ("p","الطبقة InvestmentP عبر gisapps.balady.gov.sa/opportunities/proxy/proxy.ashx → GISProjects/InvestmentView/MapServer/0."),
 ("p","تحقق من السلامة: 175 سجلاً، بدون تكرار في رقم الفرصة، 17 عموداً في المصدر، صفر صفوف تالفة (SHA-256: ae362d34c93f2723…)."),
 ("h","تواريخ"),
 ("p","LASTRFPSELLDATE و ENDDATE متطابقان في جميع السجلات الـ175، لذا يُعرض عمود واحد باسم «نهاية الفرصة»."),
 ("p","عمود «الأيام المتبقية» معادلة حيّة (=نهاية الفرصة − TODAY()) وتتحدث تلقائياً عند كل فتح للملف. القيم السالبة تعني فرصاً منتهية بعد تاريخ اللقطة."),
]
r=1
for kind,txt in LINES:
    c=m.cell(r,1,txt)
    if kind=="عنوان": c.font=Font(name="Arial",size=13,bold=True,color=BLUE); r+=2
    elif kind=="h": c.font=Font(name="Arial",size=11,bold=True,color=BLUE); r+=1
    else: c.font=BODY; c.alignment=Alignment(wrap_text=True,vertical="top"); m.row_dimensions[r].height=30; r+=1
    if kind=="h": r+=0

CAND = PAY.get("candidates", [])
if CAND:
    v = wb.create_sheet("للمراجعة"); v.sheet_view.rightToLeft = True
    v["A1"] = ("سجلات لا تُسمّي البوابة مدينتها — للمراجعة اليدوية. "
               "غير محتسبة ضمن أرقام المدن ولا ضمن الـ%d." % len(recs))
    v["A1"].font = Font(name="Arial", size=11, bold=True, color=BLUE)
    v["A2"] = ("حقل المدينة فارغ في %s من أصل %s سجل وطني مفتوح؛ صفحة الفرصة تعرض الأمانة فقط. "
               "أُدرجت هنا السجلات الواقعة ضمن %.0f كم من أقرب فرصة تُسمّيها البوابة صراحةً بإحدى "
               "المدن الأربع. القرب وحده ليس دليلاً: أحدها يبعد ٧ كم عن نقطة «الرياض» لكنه في "
               "محافظة حريملاء، والأمانة تغطي المنطقة لا المدينة."
               % (f"{PAY.get('blankCity',0):,}", f"{PAY.get('nationalOpenInvestment',0):,}",
                  PAY.get("candidateRadiusKm", 25)))
    v["A2"].font = Font(name="Arial", size=9, color="3D4C47")
    v["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    v.merge_cells("A1:I1"); v.merge_cells("A2:I2"); v.row_dimensions[2].height = 58
    CC = [("رقم الفرصة",19),("العنوان",62),("أقرب مدينة مُسمّاة",18),("المسافة (كم)",12),
          ("جهة الطرح",34),("هل تُطابق الأمانة؟",18),("آخر موعد",13),("المساحة م²",13),("الصفحة",9)]
    for i,(h,w) in enumerate(CC,1):
        c=v.cell(4,i,h); c.font=WHITE; c.fill=HDR; c.border=BOX
        c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
        v.column_dimensions[get_column_letter(i)].width=w
    v.row_dimensions[4].height=30
    for i,c_ in enumerate(CAND,5):
        ref=_s(c_.get("OPPORTUNITYID"))
        vals=[ref,_s(c_.get("OPPORTUNITYDESCRIPTION")),
              CITY_LABEL.get(c_.get("_nnCity"),c_.get("_nnCity")), c_.get("_nnKm"),
              _s(c_.get("AMANA")) or _s(c_.get("ENTITIESNAME")) or "—",
              "نعم" if c_.get("_amanahCity")==c_.get("_nnCity") else "لا",
              _s(c_.get("LASTRFPSELLDATE"))[:10], num(c_.get("TOTALSPACEINMETERS")) or None, "فتح"]
        for ci,val in enumerate(vals,1):
            cell=v.cell(i,ci,val); cell.font=BODY; cell.border=BOX
            cell.alignment=Alignment(vertical="top",wrap_text=(ci in (2,5)))
            if i%2==0: cell.fill=ZEB
        v.cell(i,4).number_format='0.0'
        v.cell(i,8).number_format='#,##0;;"—"'
        lk=v.cell(i,9); lk.hyperlink=f"https://furas.momah.gov.sa/opportunity/{ref}?type=Investment"
        lk.font=Font(name="Arial",size=10,color="1F6B4F",underline="single")
        lk.alignment=Alignment(horizontal="center",vertical="top")
    v.auto_filter.ref=f"A4:I{len(CAND)+4}"
    v.freeze_panes="A5"

wb.save(OUT)
print(f"wrote {OUT} · {len(recs)} rows"
      + (f" + {len(CAND)} for review" if CAND else ""))
