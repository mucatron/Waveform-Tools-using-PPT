import contacts
import random
import time

# Core: Actual Unicode characters from famous non-Latin scripts + some Latin-b mixes
core_unicode = [
    # Greek
    'Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ', 'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω',
    'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω',

    # Cyrillic
    'А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ё', 'Ж', 'З', 'И', 'Й', 'К', 'Л', 'М', 'Н', 'О', 'П', 'Р', 'С', 'Т', 'У', 'Ф', 'Х', 'Ц', 'Ч', 'Ш', 'Щ', 'Ъ', 'Ы', 'Ь', 'Э', 'Ю', 'Я',

    # Arabic (isolated forms for simplicity; iOS handles connected too)
    'ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي',

    # Hebrew
    'א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 'כ', 'ל', 'מ', 'נ', 'ס', 'ע', 'פ', 'צ', 'ק', 'ר', 'ש', 'ת',

    # Devanagari (some common akṣara)
    'क', 'ख', 'ग', 'घ', 'ङ', 'च', 'छ', 'ज', 'झ', 'ञ', 'ट', 'ठ', 'ड', 'ढ', 'ण', 'त', 'थ', 'द', 'ध', 'न', 'प', 'फ', 'ब', 'भ', 'म',

    # Hangul (syllables + some jamo)
    '가', '나', '다', '라', '마', '바', '사', '아', '자', '카', '타', '파', '하', 'ᄀ', 'ᄂ', 'ᄃ', 'ᄅ', 'ᄆ', 'ᄇ', 'ᄉ', 'ᄋ', 'ᄌ', 'ᄎ', 'ᄏ', 'ᄐ', 'ᄑ', 'ᄒ',

    # Thai
    'ก', 'ข', 'ฃ', 'ค', 'ฅ', 'ฆ', 'ง', 'จ', 'ฉ', 'ช', 'ซ', 'ฌ', 'ญ', 'ฎ', 'ฏ', 'ฐ', 'ฑ', 'ฒ', 'ณ', 'ด', 'ต', 'ถ', 'ท', 'ธ', 'น', 'บ', 'ป', 'ผ', 'ฝ', 'พ', 'ฟ', 'ภ', 'ม',

    # Armenian
    'Ա', 'Բ', 'Գ', 'Դ', 'Ե', 'Զ', 'Է', 'Ը', 'Թ', 'Ժ', 'Ի', 'Լ', 'Խ', 'Ծ', 'Կ', 'Հ', 'Ձ', 'Ղ', 'Ճ', 'Մ', 'Յ', 'Ն', 'Շ', 'Ո', 'Չ', 'Պ', 'Ջ', 'Ռ', 'Ս', 'Վ', 'Տ', 'Ր', 'Ց', 'Ւ', 'Փ', 'Ք', 'Օ', 'Ֆ',

    # Georgian
    'ა', 'ბ', 'გ', 'დ', 'ე', 'ვ', 'ზ', 'თ', 'ი', 'კ', 'ლ', 'მ', 'ნ', 'ო', 'პ', 'ჟ', 'რ', 'ს', 'ტ', 'უ', 'ფ', 'ქ', 'ღ', 'ყ', 'შ', 'ჩ', 'ც', 'ძ', 'წ', 'ჭ', 'ხ', 'ჯ', 'ჰ',

    # Latin-b mixes
    'Beta', 'Boris', 'Brahmi', 'Bangla', 'Bengali', 'Burmese', 'Bopomofo', 'Balinese'
]

# Unicode ranges for procedural mixing (non-Latin blocks)
unicode_ranges = [
    (0x0370, 0x03FF),   # Greek
    (0x0400, 0x04FF),   # Cyrillic
    (0x0600, 0x06FF),   # Arabic
    (0x0590, 0x05FF),   # Hebrew
    (0x0900, 0x097F),   # Devanagari
    (0xAC00, 0xD7AF),   # Hangul syllables
    (0x0E00, 0x0E7F),   # Thai
    (0x0530, 0x058F),   # Armenian
    (0x10A0, 0x10FF),   # Georgian
]

b_prefixes = ['B', 'Ba', 'Be', 'Bi', 'Bo', 'Bu', 'By', 'Bra', 'Bri', 'Bro', 'Bru', 'Bha']

def generate_unicode_mixed_name():
    if random.random() < 0.3:
        # Pure non-Latin char
        rng = random.choice(unicode_ranges)
        code = random.randint(rng[0], rng[1])
        return chr(code)
    else:
        # Latin-b prefix + non-Latin suffix char(s)
        prefix = random.choice(b_prefixes)
        suffix = ''
        for _ in range(random.randint(1, 3)):
            rng = random.choice(unicode_ranges)
            code = random.randint(rng[0], rng[1])
            suffix += chr(code)
        return prefix + suffix

SURNAME = 'while(true){ test(0) }'

def main():
    group_name = 'PerMinuteSpending'
    group_exists = any(g.name.strip().lower() == group_name.lower() for g in contacts.get_all_groups())

    if not group_exists:
        new_group = contacts.Group()
        new_group.name = group_name
        contacts.add_group(new_group)
        contacts.save()
        print(f"Created group: {group_name}")
    else:
        print(f"Using existing group: {group_name} (add contacts manually afterward)")

    all_first = set(core_unicode)

    target = 2050
    while len(all_first) < target:
        fake = generate_unicode_mixed_name()
        if 1 <= len(fake) <= 12 and fake not in all_first:  # allow short single chars
            all_first.add(fake)

    name_list = list(all_first)
    random.shuffle(name_list)

    added = 0
    skipped = 0

    for i, first in enumerate(name_list, 1):
        full = f"{first} {SURNAME}"
        if contacts.find(full):
            skipped += 1
            continue

        p = contacts.Person()
        p.first_name = first
        p.last_name = SURNAME
        p.note = "Automated PerMinuteSpending real Unicode non-Latin glyph entry"

        contacts.add_person(p)

        added += 1

        if i % 200 == 0:
            print(f"Progress: {i}/{len(name_list)} | Added: {added} | Skipped: {skipped}")
            contacts.save()
            time.sleep(0.1)

    contacts.save()
    print(f"\nDone! Added {added} contacts (skipped {skipped} duplicates).")
    print(f"Group '{group_name}' is ready — manually add contacts in batches via Contacts app.")
    print("Names now use real glyphs: Greek, Cyrillic, Arabic, Hebrew, Devanagari, Hangul, etc. + b-mixes.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("Error:", e)
        print("→ Ensure Pythonista has Contacts permission.")
