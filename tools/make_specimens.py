"""Generate the specimen illustrations (black-and-white, photocopy halftone).

Run: python tools/make_specimens.py
Writes frontend/public/objects/sNN.svg. Drop real B/W photos in at the same
paths (as .svg wrappers or by changing image_url in the catalog) to replace them.
File names are opaque on purpose so the object's name never reaches the player.
"""

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "objects"

DEFS = """<defs>
  <pattern id="ht" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="7" height="7" fill="#bdbdbd"/><circle cx="3.5" cy="3.5" r="1.9" fill="#111"/>
  </pattern>
  <pattern id="htd" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="#2a2a2a"/><circle cx="3" cy="3" r="1.3" fill="#8a8a8a"/>
  </pattern>
  <pattern id="htl" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="7" height="7" fill="#efefef"/><circle cx="3.5" cy="3.5" r="1.1" fill="#555"/>
  </pattern>
  <pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-35)">
    <rect width="8" height="8" fill="#9a9a9a"/><rect width="3" height="8" fill="#3a3a3a"/>
  </pattern>
  <linearGradient id="metal" x1="0" x2="1">
    <stop offset="0" stop-color="#5a5a5a"/><stop offset=".35" stop-color="#f4f4f4"/><stop offset=".55" stop-color="#9c9c9c"/><stop offset="1" stop-color="#3c3c3c"/>
  </linearGradient>
  <linearGradient id="metalv" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#5a5a5a"/><stop offset=".35" stop-color="#f4f4f4"/><stop offset=".6" stop-color="#9c9c9c"/><stop offset="1" stop-color="#3c3c3c"/>
  </linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="#fff"/><stop offset=".6" stop-color="#e8e8e8"/><stop offset="1" stop-color="#777"/></radialGradient>
</defs>"""

S = 'stroke="#000" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"'

ITEMS: dict[str, str] = {}

# s01 toothbrush
bristles = "".join(
    f'<rect x="{316 + i * 6.6:.1f}" y="{142 + (i % 2) * 4}" width="5" height="{46 - (i % 2) * 4}" fill="{"#fff" if i % 3 else "#d0d0d0"}" stroke="#000" stroke-width="1.6"/>'
    for i in range(8)
)
ITEMS["s01"] = f"""<g transform="rotate(-30 200 200)">
<rect x="36" y="184" width="262" height="32" rx="16" fill="#e6e6e6" {S}/>
<rect x="70" y="190" width="104" height="20" rx="10" fill="url(#ht)" stroke="#000" stroke-width="2.5"/>
<rect x="290" y="192" width="30" height="16" fill="#e6e6e6" {S}/>
<rect x="308" y="186" width="68" height="24" rx="9" fill="#f5f5f5" {S}/>
{bristles}
<path d="M46 194 Q 140 188 280 192" stroke="#fff" stroke-width="4" fill="none"/>
</g>"""

# s02 umbrella
ITEMS["s02"] = f"""<path d="M50 190 Q 200 20 350 190 Q 325 172 300 190 Q 275 172 250 190 Q 225 172 200 190 Q 175 172 150 190 Q 125 172 100 190 Q 75 172 50 190 Z" fill="url(#htd)" {S}/>
<path d="M200 60 Q 160 120 150 190 M200 60 Q 240 120 250 190 M200 60 Q 110 110 100 190 M200 60 Q 290 110 300 190" stroke="#000" stroke-width="3" fill="none"/>
<path d="M120 120 Q 160 80 200 64" stroke="#d8d8d8" stroke-width="5" fill="none" opacity=".7"/>
<line x1="200" y1="38" x2="200" y2="60" {S}/>
<path d="M200 190 L200 330 Q 200 362 228 362 Q 254 362 254 336" fill="none" stroke="#000" stroke-width="12" stroke-linecap="round"/>
<path d="M200 190 L200 330 Q 200 362 228 362 Q 254 362 254 336" fill="none" stroke="#7a7a7a" stroke-width="6" stroke-linecap="round"/>"""

# s03 seatbelt
ITEMS["s03"] = f"""<path d="M10 40 L150 175 L190 140 L50 5 Z" fill="url(#hatch)" {S}/>
<rect x="150" y="150" width="92" height="64" rx="10" transform="rotate(43 196 182)" fill="url(#metal)" {S}/>
<rect x="182" y="168" width="34" height="12" rx="5" transform="rotate(43 196 182)" fill="#222" stroke="#000" stroke-width="3"/>
<path d="M232 228 L262 198 L300 236 L270 266 Z" fill="url(#metal)" {S}/>
<rect x="250" y="210" width="126" height="92" rx="20" transform="rotate(43 313 256)" fill="#1b1b1b" {S}/>
<rect x="282" y="226" width="54" height="22" rx="8" transform="rotate(43 313 256)" fill="url(#ht)" stroke="#000" stroke-width="3"/>
<path d="M330 300 L370 392 L330 400 L300 320 Z" fill="url(#hatch)" {S}/>"""

# s04 zipper
teeth = []
for i in range(14):
    y = 70 + i * 20
    gap = max(0, (6 - i)) * 9 if i < 6 else 0
    teeth.append(f'<rect x="{176 - gap}" y="{y}" width="26" height="11" rx="3" fill="url(#metal)" stroke="#000" stroke-width="2.5"/>')
    teeth.append(f'<rect x="{198 + gap}" y="{y + 10}" width="26" height="11" rx="3" fill="url(#metal)" stroke="#000" stroke-width="2.5"/>')
ITEMS["s04"] = f"""<path d="M70 30 L176 30 L176 380 L120 380 Z" fill="url(#ht)" {S}/>
<path d="M330 30 L224 30 L224 380 L280 380 Z" fill="url(#ht)" {S}/>
<path d="M150 30 L194 190 L206 190 L250 30 Z" fill="#f2f2f2" stroke="#000" stroke-width="3"/>
{''.join(teeth)}
<path d="M174 182 L226 182 L218 236 L182 236 Z" fill="url(#metal)" {S}/>
<rect x="188" y="230" width="24" height="70" rx="10" fill="url(#metal)" {S}/>
<rect x="194" y="270" width="12" height="20" rx="5" fill="#111"/>"""

# s05 fork
ITEMS["s05"] = f"""<g transform="rotate(14 200 200)">
<path d="M150 30 L150 120 Q 150 165 186 178 L190 360 Q 200 384 210 360 L214 178 Q 250 165 250 120 L250 30 L238 30 L238 118 L226 118 L226 30 L214 30 L214 118 L206 118 L206 30 L194 30 L194 118 L186 118 L186 30 L174 30 L174 118 L162 118 L162 30 Z" fill="url(#metal)" {S}/>
<path d="M200 190 L200 350" stroke="#fff" stroke-width="5"/>
</g>"""

# s06 elevator
btn = "".join(f'<circle cx="338" cy="{150 + i * 34}" r="11" fill="{"url(#glow)" if i == 1 else "#cfcfcf"}" stroke="#000" stroke-width="3"/>' for i in range(4))
ITEMS["s06"] = f"""<rect x="40" y="30" width="270" height="350" fill="#efefef" {S}/>
<rect x="66" y="80" width="218" height="300" fill="#151515" {S}/>
<rect x="66" y="80" width="98" height="300" fill="url(#metal)" {S}/>
<rect x="186" y="80" width="98" height="300" fill="url(#metal)" {S}/>
<rect x="164" y="80" width="22" height="300" fill="url(#htd)"/>
<rect x="120" y="42" width="110" height="26" rx="4" fill="#111" {S}/>
<path d="M160 62 L170 48 L180 62 Z M190 48 L200 62 L210 48 Z" fill="#fff"/>
<rect x="318" y="126" width="40" height="150" rx="8" fill="url(#metalv)" {S}/>{btn}"""

# s07 traffic light
ITEMS["s07"] = f"""<rect x="186" y="320" width="28" height="80" fill="url(#metal)" {S}/>
<rect x="136" y="20" width="128" height="306" rx="22" fill="#1a1a1a" {S}/>
<circle cx="200" cy="82" r="38" fill="#3a3a3a" {S}/>
<circle cx="200" cy="174" r="38" fill="#3a3a3a" {S}/>
<circle cx="200" cy="266" r="38" fill="url(#glow)" {S}/>
<path d="M156 66 Q 200 30 244 66 L 252 52 Q 200 12 148 52 Z M156 158 Q 200 122 244 158 L 252 144 Q 200 104 148 144 Z M156 250 Q 200 214 244 250 L 252 236 Q 200 196 148 236 Z" fill="#111" stroke="#000" stroke-width="2"/>
<circle cx="200" cy="266" r="60" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="4 8" opacity=".9"/>"""

# s08 passport
ITEMS["s08"] = f"""<g transform="rotate(-8 200 200)">
<rect x="120" y="60" width="210" height="290" rx="10" fill="#f6f6f6" {S}/>
<rect x="250" y="190" width="70" height="70" rx="6" fill="none" stroke="#555" stroke-width="3" stroke-dasharray="6 4" transform="rotate(12 285 225)"/>
<rect x="90" y="40" width="210" height="300" rx="14" fill="url(#htd)" {S}/>
<circle cx="195" cy="160" r="52" fill="none" stroke="#d8d8d8" stroke-width="4"/>
<ellipse cx="195" cy="160" rx="22" ry="52" fill="none" stroke="#d8d8d8" stroke-width="3"/>
<path d="M143 160 L247 160 M152 132 L238 132 M152 188 L238 188" stroke="#d8d8d8" stroke-width="3"/>
<rect x="140" y="250" width="110" height="10" fill="#d8d8d8"/><rect x="160" y="272" width="70" height="8" fill="#d8d8d8"/>
<rect x="150" y="300" width="90" height="16" rx="3" fill="none" stroke="#d8d8d8" stroke-width="3"/>
</g>"""

# s09 headphones
ITEMS["s09"] = f"""<path d="M90 240 Q 90 60 200 60 Q 310 60 310 240" fill="none" stroke="#000" stroke-width="30" stroke-linecap="round"/>
<path d="M90 240 Q 90 60 200 60 Q 310 60 310 240" fill="none" stroke="#bdbdbd" stroke-width="20" stroke-linecap="round"/>
<path d="M110 120 Q 140 76 200 72" fill="none" stroke="#fff" stroke-width="5"/>
<rect x="52" y="210" width="80" height="128" rx="34" fill="url(#htd)" {S}/>
<rect x="268" y="210" width="80" height="128" rx="34" fill="url(#htd)" {S}/>
<rect x="112" y="226" width="34" height="96" rx="14" fill="url(#ht)" {S}/>
<rect x="254" y="226" width="34" height="96" rx="14" fill="url(#ht)" {S}/>"""

# s10 shopping cart
grid = "".join(f'<line x1="{x}" y1="120" x2="{x + (x - 200) * 0.08:.0f}" y2="260" stroke="#000" stroke-width="2.5"/>' for x in range(96, 330, 22))
grid += "".join(f'<line x1="{80 + i * 3}" y1="{120 + i * 23}" x2="{336 - i * 4}" y2="{120 + i * 23}" stroke="#000" stroke-width="2.5"/>' for i in range(7))
ITEMS["s10"] = f"""<path d="M20 80 L60 80 L80 120" fill="none" stroke="#000" stroke-width="10" stroke-linecap="round"/>
<path d="M20 80 L60 80 L80 120" fill="none" stroke="#aaa" stroke-width="5" stroke-linecap="round"/>
<path d="M80 120 L340 120 L310 262 L104 262 Z" fill="#e9e9e9" opacity=".6"/>
{grid}
<path d="M80 120 L340 120 L310 262 L104 262 Z" fill="none" {S}/>
<path d="M104 262 L110 310 L320 310" fill="none" stroke="#000" stroke-width="7"/>
<circle cx="130" cy="340" r="22" fill="#1b1b1b" {S}/><circle cx="130" cy="340" r="7" fill="#ccc"/>
<circle cx="296" cy="340" r="22" fill="#1b1b1b" {S}/><circle cx="296" cy="340" r="7" fill="#ccc"/>"""

# s11 doorbell
grille = "".join(f'<circle cx="{180 + (i % 4) * 14}" cy="{100 + (i // 4) * 14}" r="3.4" fill="#111"/>' for i in range(12))
ITEMS["s11"] = f"""<rect x="0" y="0" width="400" height="400" fill="url(#htl)"/>
<rect x="128" y="50" width="144" height="300" rx="26" fill="url(#metalv)" {S}/>
{grille}
<circle cx="200" cy="250" r="54" fill="#1a1a1a" {S}/>
<circle cx="200" cy="250" r="40" fill="url(#glow)" stroke="#000" stroke-width="3"/>
<circle cx="200" cy="250" r="47" fill="none" stroke="#fff" stroke-width="3"/>"""

# s12 remote
rb = "".join(f'<rect x="{150 + (i % 3) * 36}" y="{210 + (i // 3) * 30}" width="26" height="18" rx="6" fill="#d6d6d6" stroke="#000" stroke-width="2.5"/>' for i in range(9))
ITEMS["s12"] = f"""<g transform="rotate(12 200 200)">
<rect x="130" y="20" width="140" height="360" rx="34" fill="#1d1d1d" {S}/>
<path d="M146 46 Q 150 32 170 30" stroke="#777" stroke-width="5" fill="none"/>
<circle cx="236" cy="56" r="12" fill="url(#glow)" stroke="#000" stroke-width="3"/>
<circle cx="200" cy="134" r="44" fill="url(#ht)" stroke="#000" stroke-width="3"/>
<circle cx="200" cy="134" r="17" fill="#e6e6e6" stroke="#000" stroke-width="3"/>
{rb}
<rect x="170" y="318" width="60" height="22" rx="10" fill="#d6d6d6" stroke="#000" stroke-width="2.5"/>
</g>"""

# s13 telescope
ITEMS["s13"] = f"""<path d="M200 230 L120 390 M200 230 L280 390 M200 230 L205 392" stroke="#000" stroke-width="10" stroke-linecap="round"/>
<path d="M200 230 L120 390 M200 230 L280 390 M200 230 L205 392" stroke="#9a9a9a" stroke-width="5" stroke-linecap="round"/>
<g transform="rotate(-32 200 200)">
<rect x="70" y="170" width="250" height="62" rx="8" fill="#f2f2f2" {S}/>
<rect x="300" y="160" width="62" height="82" rx="8" fill="url(#htd)" {S}/>
<rect x="40" y="186" width="34" height="30" fill="url(#htd)" {S}/>
<rect x="20" y="192" width="22" height="18" fill="#1a1a1a" {S}/>
<rect x="140" y="144" width="90" height="20" rx="6" fill="url(#ht)" {S}/>
<rect x="80" y="176" width="220" height="10" fill="#fff"/>
<rect x="170" y="230" width="40" height="22" fill="#1a1a1a" {S}/>
</g>"""

# s14 satellite dish
ITEMS["s14"] = f"""<rect x="300" y="20" width="90" height="370" fill="url(#htl)" {S}/>
<path d="M300 250 L250 250 L230 270" fill="none" stroke="#000" stroke-width="12"/>
<g transform="rotate(-24 170 200)">
<ellipse cx="170" cy="200" rx="128" ry="150" fill="url(#ht)" {S}/>
<ellipse cx="170" cy="200" rx="96" ry="118" fill="#e8e8e8" stroke="#000" stroke-width="2.5" opacity=".9"/>
<path d="M120 110 Q 92 160 104 236" stroke="#fff" stroke-width="7" fill="none"/>
</g>
<path d="M170 290 L80 150" stroke="#000" stroke-width="9"/>
<path d="M170 290 L80 150" stroke="#aaa" stroke-width="4"/>
<rect x="50" y="118" width="46" height="40" rx="8" transform="rotate(-30 73 138)" fill="#1a1a1a" {S}/>"""

# s15 screwdriver
ridges = "".join(f'<rect x="{62 + i * 18}" y="186" width="9" height="28" rx="4" fill="#111"/>' for i in range(7))
ITEMS["s15"] = f"""<g transform="rotate(-36 200 200)">
<path d="M40 176 Q 30 200 40 224 L180 230 Q 196 200 180 170 Z" fill="url(#ht)" {S}/>
{ridges}
<rect x="176" y="190" width="24" height="20" fill="#1a1a1a" {S}/>
<rect x="198" y="193" width="160" height="14" fill="url(#metalv)" {S}/>
<path d="M356 191 L382 194 L382 206 L356 209 Z" fill="url(#metalv)" {S}/>
</g>"""

# s16 vending machine
items = "".join(
    f'<rect x="{92 + c * 44}" y="{70 + r * 62}" width="32" height="40" rx="{4 if (r + c) % 2 else 14}" fill="{["url(#ht)", "#e8e8e8", "url(#htd)"][(r * 3 + c) % 3]}" stroke="#000" stroke-width="2.5"/>'
    + f'<path d="M{86 + c * 44} {116 + r * 62} q 11 -6 22 0 q 11 6 22 0" fill="none" stroke="#555" stroke-width="2"/>'
    for r in range(4) for c in range(4)
)
keys = "".join(f'<rect x="{292 + (i % 3) * 16}" y="{140 + (i // 3) * 16}" width="11" height="11" fill="#ddd" stroke="#000" stroke-width="1.6"/>' for i in range(12))
ITEMS["s16"] = f"""<rect x="60" y="20" width="290" height="372" rx="8" fill="#1a1a1a" {S}/>
<rect x="78" y="46" width="196" height="262" fill="#f4f4f4" {S}/>
{items}
<path d="M90 60 L130 300" stroke="#fff" stroke-width="8" opacity=".6"/>
<rect x="286" y="60" width="52" height="48" fill="url(#glow)" {S}/>
{keys}
<rect x="300" y="222" width="24" height="40" rx="3" fill="#111" stroke="#bbb" stroke-width="2"/>
<rect x="96" y="326" width="160" height="44" rx="4" fill="url(#htd)" {S}/>"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, body in ITEMS.items():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" role="img" aria-label="Specimen">{DEFS}{body}</svg>'
        (OUT / f"{key}.svg").write_text(svg)
    print(f"wrote {len(ITEMS)} specimens to {OUT}")


if __name__ == "__main__":
    main()
