#!/bin/bash
# VertiStrat Solutions: check domain DNS (Squarespace), website (Lovable) and email auth (Google Workspace).
# Usage: vertistrat_status.sh
D=vertistratsolution.com
NS=nsb1.squarespacedns.com
LOVABLE_IP=185.158.133.1
ok() { [ "$1" = yes ] && echo "  OK   $2" || echo "  TODO $2"; }

a=$(dig +short @$NS $D A | sort | tr '\n' ' ')
w=$(dig +short @$NS www.$D | sort | tr '\n' ' ')
echo "Website DNS (authoritative, Squarespace)"
echo "  @   A    : $a"; echo "  www      : $w"
ok "$([ "$a" = "$LOVABLE_IP " ] && echo yes)" "apex points only to Lovable ($LOVABLE_IP)"
ok "$([ "$w" = "$LOVABLE_IP " ] && echo yes)" "www points only to Lovable"
ok "$(dig +short @$NS _lovable.$D TXT | grep -q lovable_verify && echo yes)" "_lovable TXT present"
ok "$(dig +short @$NS _lovable.www.$D TXT | grep -q lovable_verify && echo yes)" "_lovable.www TXT present"

echo "Email (Google Workspace, contact@$D)"
ok "$(dig +short @$NS $D MX | grep -q smtp.google.com && echo yes)" "MX -> smtp.google.com"
ok "$(dig +short @$NS $D TXT | grep -q _spf.google.com && echo yes)" "SPF"
ok "$(dig +short @$NS google._domainkey.$D TXT | grep -q DKIM1 && echo yes)" "DKIM (google._domainkey)"
ok "$(dig +short @$NS _dmarc.$D TXT | grep -q DMARC1 && echo yes)" "DMARC"

echo "Live sites"
for u in https://$D https://www.$D https://vertistrat.lovable.app; do
  t=$(curl -sL -m 15 "$u" | grep -io '<title>[^<]*' | head -1 | sed 's/<title>//I')
  c=$(curl -sL -m 15 -o /dev/null -w '%{http_code}' "$u")
  echo "  $c  $u  — ${t:-no title}"
done
