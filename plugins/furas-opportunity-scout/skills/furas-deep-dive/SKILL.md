---
name: furas-deep-dive
description: Deep-dive one specific Furas investment opportunity by its reference number — retrieve and read its كراسة الشروط والمواصفات, extract the commercial terms the dashboard cannot show, and describe its location. Use when the user names a رقم الفرصة such as "06-26-185770-12001", or says "deep dive on this opportunity", "get me the كراسة for", "what are the terms on", "tell me more about opportunity", or "where exactly is".
---

# Deep dive on one opportunity

Run only when the user names a specific رقم الفرصة. Never do this for a whole table.

## Why this exists

The dashboard shows what exists and when it closes. It cannot answer whether an opportunity
is worth bidding on, because the portal does not publish annual rent, minimum guarantee or
revenue-share terms at list level. Those live inside the كراسة. This skill opens it.

## Steps

1. **Locate the record** in the latest `runs/*/data.json`. If absent, say so — it may have
   closed since the last scan. Restate the رقم الفرصة in every output so it traces back.

2. **Open the opportunity page**: `https://furas.momah.gov.sa/opportunity/{ref}?type=Investment`
   (the `?type=` is required). Its `المرفقات` tab lists the documents.

3. **Retrieve every document, and hand the files to the user.** The `المرفقات` tab usually
   holds كراسة الشروط والمواصفات and sometimes مسودة العقد. Download each one and **deliver the
   actual files with SendUserFile** alongside your written analysis — the user asked about this
   opportunity; they get the source documents, not only your summary.

   **Measured 30 Aug 2026: only about a quarter of booklets can be fetched headlessly.**
   A paced sample of 12 across all four cities returned **3** — الرياض 1/3, جدة 1/3,
   مكة 1/3, المدينة المنورة **0/3** — each retried 3× with pauses. Treat retrieval as
   likely-to-fail and plan the escalation, rather than assuming a retry will rescue it.

   Two routes, and only one can ever work:

   - **The direct attachment URL never returns the file.** It answers `200` with
     `Content-Type: text/html` and ~1.14 MB of the portal's page shell. Do not waste
     retries on it.
   - **The static path is the only headless route that works:** from an attachment URL of
     the shape `/opportunity/attachment/{ref}/{fileId}/{name}/{ext}`, build

     ```
     https://furas.momah.gov.sa/sites/default/files/{fileId}_{name}.{ext}
     ```

     Percent-encode it and **preserve the filename exactly, including any trailing space** —
     several booklets are stored with one. Take the `fileId` from the page's own href; never
     guess it. When this 404s, the file is genuinely not on that path — probed variants
     (space stripped, no fileId, dated `2026-08/` subdirectory, underscored name) all 404 too.

   **Fetch as raw bytes.** Read the response with `urlopen(...).read()` into `bytes` and check
   `data[:5] == b"%PDF-"`. Never decode the response as text first: `decode("utf-8","replace")`
   corrupts the file while *still passing a `"%PDF"` string check*, and silently inflated a
   1,410,705-byte booklet to 2,452,026 bytes of mojibake in testing. A size that disagrees with
   a second fetch is the tell.

   **Retry twice, then escalate — do not keep hammering.** Rapid repeated requests appear to
   trip rate-limiting: a batch of 24 fast probes returned 0/24 including a file that had
   downloaded completely minutes earlier and downloaded completely again after a pause. Space
   requests ~5 s apart.

   **When retrieval fails, say so precisely.** The correct sentence is *"the portal lists this
   document but will not serve it to an automated request"* — never *"the document is
   unavailable"* and never *"this opportunity has no كراسة"*. The portal's own attachment
   archive is partly broken; that is a portal fault, not evidence about the opportunity.
   Then give the user the opportunity-page link so they can download it in a browser, where it
   generally works. If a Chrome browser tool is connected, offer to fetch it that way first.

   **Never substitute.** Do not hand over a different opportunity's booklet, a cached one, or a
   summary presented as if the document had been read. If the file was not retrieved, no
   commercial terms are reported from it — say what is missing and stop.

   Arabic PDFs extract in reversed visual order with most tools. Use
   `pdftotext -layout -enc UTF-8`, which preserves correct RTL order — pdfplumber and pypdf
   return the text mirrored and will produce nonsense.

   **Then normalise before searching.** Some booklets (Word-generated, certain embedded fonts)
   extract with the definite article bound to the following letter, so `المواصفات` comes out as
   `املواصفات` and `المساحة` as `املساحة`. Exact-string search then returns **zero for every
   Arabic keyword** and the document looks empty or wrongly structured. Others pad words with
   tatweel (`حـــدود`). Use the helper:

   ```python
   import sys; sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/scripts")
   from ar_text import norm, find      # find(haystack, needle) normalises both sides
   ```

   Measured on a Riyadh booklet: `المواصفات` 0 → 102 hits, `المساحة` 0 → 3, `حدود العقار` 0 → 1.
   **If an Arabic keyword returns 0, suspect the extraction before concluding the section is
   absent.**

4. **Read it and extract** what the dashboard cannot: contract term and renewal, annual value
   or minimum guarantee, revenue-share basis and percentage, permitted and prohibited uses,
   deposit and bid-bond, construction obligations and timelines, penalties, evaluation
   criteria and weightings, and the submission mechanics. Quote figures exactly. Anything not
   stated is `غير مذكور`.

5. **Location — read the booklet, do not stop at the record.** The GIS coordinates in
   `data.json` are the starting point, not the answer. Work through this in order:

   a. **Expect the contract body to be blank, and do not rely on one heading.** The property
      table is a template with street, plan number, plot number, all four حدود العقار and their
      أطوال left empty. Its heading and contents vary by amanah — verified examples:

      | Issuer | Heading | Coordinate row |
      |---|---|---|
      | أمانة محافظة جدة | `البند الرابع: وصف العقار` | X / Y → «حسب القرار المساحي المرفق» |
      | أمانة منطقة الرياض | `المادة الثالثة: وصف العقار` | **no coordinate row at all** |

      Search for `وصف العقار` **normalised**, not for a section number. A blank field or a
      cross-reference is **not** a missing value — do not report غير مذكور and move on.
      Riyadh also carries the plan and plot in the document's own subject line
      (`بالمخطط رقم (2702) بحي عريض`, `رمز القطعة (13473439)`) — read that too.

   b. **The القرار المساحي is usually bound into the same PDF**, near the end, under a heading
      like `المخطط العام للموقع (الرسم الكروكي للموقع)` — one stamped survey sheet per plot.
      **These are scanned images with no extractable text**, so `pdftotext` finds nothing and a
      keyword search for `إحداثيات` will look like a dead end. Find them with:

      ```bash
      pdfimages -list booklet.pdf | awk 'NR>2 && $4>1000 && $5>800 {print "page",$1,$4"x"$5}'
      pdftoppm -f <page> -l <page> -r 400 -png booklet.pdf pg    # then Read the PNG and look
      ```

   c. **Read the corner-coordinate table off the rendered image. Its format varies by amanah** —
      do not search for one fixed heading:

      - **جدة / NCVC style:** «إحداثيات الموقع حسب نظام إحداثيات خرائط الاعتماد المعدل NGN»,
        paired شرقيات / شماليات per corner, given twice (`بموجب القرار المساحي` and
        `بموجب الطبيعة`), **Arabic-Indic digits** (٠١٢٣٤٥٦٧٨٩), often handwritten annotations.
      - **الرياض style:** a GIS-produced sheet with **«احداثيات حدود الموقع»** (NO. / EASTING /
        NORTHING), a separate **`LIST OF CONTROL POINTS`** table in English with elevations, a
        **`جدول الحدود والأطوال`** giving each side's street width and length, aerial photos, a
        key map, and **`WGS84` printed explicitly**. Latin digits, far easier to read.

      Whatever the format, crop and enlarge before reading.

   d. **Convert and cross-check — and pick the UTM zone by longitude.** Saudi spans two zones,
      and using the wrong one puts the site about **600 km** away:

      | Cities | Zone | EPSG |
      |---|---|---|
      | جدة · مكة المكرمة · المدينة المنورة (lon < 42°E) | 37N | **32637** |
      | الرياض (lon ≥ 42°E) | 38N | **32638** |

      Do not hardcode either. Use the helper, which selects the zone and does the comparison:

      ```python
      from ar_text import check_against_gis, polygon_area
      lat, lon, metres, epsg = check_against_gis(corners, rec["_lat"], rec["_lon"])
      ```

      **Verified results — both agree to within ~50 m:**

      | Opportunity | Zone | Separation from GIS point |
      |---|---|---|
      | `01-26-005001-4004` (جدة, 159,701 m²) | 37N | **44 m** |
      | `01-26-004001299-7002` (الرياض, 82,142 m²) | 38N | **50 m** |

      Agreement within roughly the parcel's own dimension confirms both sources. Hundreds of
      metres means a misread digit; hundreds of **kilometres** means the wrong zone. Ain el Abd
      1970 (EPSG:20437) came out ~120 m off, so prefer WGS84 and state which you used.

      **Third check: area.** Run `polygon_area(corners)` and compare with the المساحة on the
      survey sheet and in the portal record. On the Riyadh case all three agreed
      (81,787 m² computed vs 82,142.06 m² stated in both) — a >2% gap means corners were
      misread or the boundary has more vertices than you captured.

   e. **Never quote a digit you cannot read.** These are stamped, hand-annotated scans. If the
      last digits of a boundary length are ambiguous, say so and **deliver the rendered survey
      page as an image** so the reader can check it, rather than publishing a number you guessed.

   f. **Then describe the setting** — district, what each side adjoins (a road of stated width,
      a vacant plot, a neighbouring parcel), and the plot's position in its subdivision. Do not
      invent boundaries the sources do not state.

6. **Check how the award is actually decided** before writing the read. Do not assume it is a
   highest-price auction — on at least one verified booklet the scoring table carried **no
   price criterion at all** and the award went to the highest *technical* score, with 40% of
   the marks on the master plan alone. Read the evaluation table and say plainly what wins it.

7. **Close with a short read**: what kind of investor this suits and the two or three things
   that would decide it. Flag anything unusual in the terms, and name what must be established
   before committing.

## The booklet's scanned annexes carry more than location

Whatever is bound in as an image is invisible to text extraction — survey decisions, site
sketches, plot layouts, sometimes approval letters and technical annexes. After extracting text,
**always run `pdfimages -list` and render any large image pages**, then look at them. A booklet
that appears to omit something is often just storing it as a picture.

## Deliverables

Every deep dive returns: the written analysis, **the actual document files**, any survey or
site-plan pages **rendered as images**, the coordinates with a maps link and the cross-check
result, and the رقم الفرصة restated for traceability.

## Constraints

- Never log in, register, or complete Nafath to reach a document. If purchase or
  authentication is required, stop and report that.
- Never estimate a commercial figure. The whole point is the real numbers.
- Quote the booklet accurately; do not paraphrase a number into a different one.
