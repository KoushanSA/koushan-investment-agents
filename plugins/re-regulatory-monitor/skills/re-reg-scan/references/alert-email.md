# Alert email

One email per new decision. Send with `outlook_send_mail`, `bodyType: "html"`.

- **To:** every address in `alert_to` from `claude/re_reg_monitor_config.json`
- **Subject:** `قرار عقاري جديد: <عنوان مختصر>` — the short title is the decision's title trimmed to about 70 characters, without the issuer.
- **Body (HTML, RTL)** — replace `<LIBRARY_URL>` with `library_url` and `<SENDER_NAME>` with `sender_name` from the config:

```html
<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif">
<p><b><TITLE></b><br><ISSUER> — <ISSUED></p>
<p><SUMMARY LINE 1><br><SUMMARY LINE 2></p>
<p>التصنيف في المكتبة: <فعّال | غير مؤكد — <REASON> | سابق/ملغى></p>
<p>القرارات الفعّالة (الرابط الدائم): <a href="<LIBRARY_URL>#active"><LIBRARY_URL>#active</a><br>
المصدر الرسمي: <a href="<URL>"><SOURCE></a></p>
<hr>
<p style="color:#666;font-size:12px">رسالة آلية ضمن التحديث الأسبوعي لمكتبة القرارات العقارية، أرسلها وكيل الرصد (Claude) عبر حساب <SENDER_NAME> في Outlook. لا حاجة للرد عليها.<br>
Automated message from the Real Estate Regulatory Monitor agent, part of the weekly decisions-library update, sent via <SENDER_NAME>'s mailbox. No reply needed.</p>
</div>
```

Rules:
- If the decision has no direct link, replace the source line with «المصدر الرسمي: تعذّر الوصول لرابط مباشر (<SOURCE>)». Never put a guessed link.
- Keep the summary to the two lines stored in the record. No extra commentary.
- Escape `<`, `>` and `&` in inserted text.
- Never send for baseline rows, known ids, status changes, or when the run could not read state.
- Recipients must be able to open the library: remind the owner to share the artifact with them if they haven't.
