from pathlib import Path
p=Path('/opt/korea365/control_center/templates/account_schedule.html');s=p.read_text();needle='<div>지난달 합계:'
assert needle in s
if '{{c.audience_error}}' not in s:
 p.with_suffix('.html.pre-windsor-status').write_text(s)
 s=s.replace(needle,'{% if c.audience_error %}<div class="muted">{{c.audience_error}}</div>{% endif %}'+needle,1);p.write_text(s)
print('template status added')

