"""Palestine solidarity tab HTML (Qt QTextBrowser) - resources and framing."""
from __future__ import annotations

import html

from smd.help_content import _BODY, _SECTION, _TOC, _callout, headed_title


def _resource_link(name: str, url: str, blurb: str) -> str:
    safe_name = html.escape(name)
    safe_url = html.escape(url, quote=True)
    return (
        "<li style='margin-bottom:14px;'>"
        f'<a href="{safe_url}"><b>{safe_name}</b></a>'
        f"<div style='font-size:14px; line-height:1.5; opacity:0.92; margin-top:4px;'>{blurb}</div>"
        "</li>"
    )


def _phrase_list(items: list[str]) -> str:
    rows = "".join(f"<li>{html.escape(text)}</li>" for text in items)
    return f"<ul style='margin:12px 0 8px 22px; padding:0;'>{rows}</ul>"


def _bullet_block(items: list[tuple[str, str]]) -> str:
    """Title + detail bullets for oppression/aspect lists."""
    rows = []
    for title, detail in items:
        rows.append(
            "<li style='margin-bottom:10px;'>"
            f"<b>{html.escape(title)}</b> — {detail}"
            "</li>"
        )
    return f"<ul style='margin:12px 0 8px 22px; padding:0;'>{''.join(rows)}</ul>"


def build_palestine_html(*, accent: str | None = None) -> str:
    solidarity_phrases = [
        "Free Palestine — end the occupation.",
        "Oppose Israeli government policy in Palestine.",
        "Hold Israel accountable for violations of international law.",
        "Documented human rights violations in Palestine must stop.",
        "Stop the killing and forced displacement in Gaza and the West Bank.",
        "Oppose the occupation and illegal settlements.",
        "Support Palestinian rights and self-determination.",
        "Stand with Palestinians against displacement and apartheid.",
        "Protect journalists reporting from Palestine — their killing must be investigated.",
    ]

    oppression_aspects = [
        (
            "Military occupation & annexation",
            "Decades of Israeli control over the West Bank, including East Jerusalem; "
            "expanding settlements on occupied land (widely considered illegal under "
            "international law).",
        ),
        (
            "Gaza blockade",
            "Since 2007, severe restrictions on movement of people and goods — "
            "documented as collective punishment affecting water, power, medical "
            "supplies, and reconstruction.",
        ),
        (
            "Forced displacement & home demolitions",
            "Palestinian communities displaced for settlements, military zones, "
            "and punitive demolitions — tracked by UN OCHA and human-rights groups.",
        ),
        (
            "Settler violence & land seizures",
            "Attacks on Palestinian villages, olive groves, and property in the "
            "West Bank, often alongside state-backed settlement expansion.",
        ),
        (
            "Movement restrictions & checkpoints",
            "Permit systems, the separation barrier, and checkpoints that restrict "
            "daily life, work, and medical access in the West Bank.",
        ),
        (
            "Detention without trial",
            "Administrative detention, military courts for children, and poor "
            "conditions documented by Addameer, B'Tselem, and UN bodies.",
        ),
        (
            "Access to healthcare & humanitarian aid",
            "Attacks on hospitals, aid convoys, and UN facilities — monitored by "
            "WHO, UNRWA, and ICRC in conflict periods.",
        ),
        (
            "Apartheid & unequal legal systems",
            "Separate legal frameworks for Israelis and Palestinians in the "
            "occupied territories — analyzed by Amnesty, HRW, and B'Tselem.",
        ),
        (
            "Destruction of cultural & religious sites",
            "Damage to mosques, churches, archives, universities, and heritage "
            "during military operations — reported by UNESCO partners and local NGOs.",
        ),
        (
            "Economic strangulation",
            "Restrictions on farming, fishing zones off Gaza, export controls, "
            "and destruction of infrastructure that keeps Palestinian economies "
            "dependent and impoverished.",
        ),
    ]

    journalist_resources = [
        (
            "Committee to Protect Journalists (CPJ)",
            "https://cpj.org/",
            "Tracks journalists killed, injured, detained, or missing worldwide — "
            "including extensive documentation of media workers killed in Gaza and "
            "the West Bank. CPJ has called for independent investigations into "
            "journalist deaths and attacks on press freedom.",
        ),
        (
            "CPJ — Israel and the occupied territories",
            "https://cpj.org/regions/middle-east-and-north-africa/israel-and-the-occupied-territories/",
            "Regional hub: killed journalists, impunity, and safety advisories.",
        ),
        (
            "Reporters Without Borders (RSF)",
            "https://rsf.org/en/region/middle-east",
            "Press-freedom rankings, alerts on journalist killings, and campaigns "
            "for protection of reporters in conflict zones including Palestine.",
        ),
        (
            "International Federation of Journalists (IFJ)",
            "https://www.ifj.org/",
            "Global union body documenting safety violations and advocating for "
            "journalists under fire.",
        ),
    ]

    whistleblower_resources = [
        (
            "Breaking the Silence",
            "https://www.breakingthesilence.org.il/",
            "Israeli veterans who publish firsthand testimonies about military service "
            "in the occupied territories — one of the most direct insider accounts "
            "of day-to-day occupation policy.",
        ),
        (
            "B'Tselem — testimonies & reports",
            "https://www.btselem.org/",
            "Israeli organization whose researchers and field workers document "
            "violations; staff have faced harassment for exposing state conduct.",
        ),
        (
            "+972 Magazine",
            "https://www.972mag.com/",
            "Independent journalism by Israelis and Palestinians, including "
            "investigative pieces on military policy, surveillance, and dissent.",
        ),
        (
            "Al-Haq — legal documentation",
            "https://www.alhaq.org/",
            "Palestinian human-rights lawyers who submit evidence to the ICC and "
            "UN — effectively whistleblowing through formal legal channels.",
        ),
        (
            "Human Rights Watch — Israel/Palestine",
            "https://www.hrw.org/middle-east/north-africa/israel/palestine",
            "Investigative reports often based on leaked documents, soldier "
            "testimony, and satellite evidence.",
        ),
    ]

    bds_resources = [
        (
            "BDS Movement",
            "https://bdsmovement.net/",
            "Palestinian-led Boycott, Divestment, Sanctions campaign — modeled on "
            "anti-apartheid boycotts. Calls for economic pressure until Israel meets "
            "obligations under international law (end occupation, equal rights, "
            "right of return).",
        ),
        (
            "BDS — What is BDS?",
            "https://bdsmovement.net/what-is-bds",
            "Plain-language explainer of the three demands and how boycott, "
            "divestment, and sanctions work in practice.",
        ),
        (
            "Who Profits",
            "https://www.whoprofits.org/",
            "Research center exposing corporate involvement in the occupation "
            "(settlements, checkpoints, prisons) — used to inform boycott targets.",
        ),
        (
            "American Friends Service Committee (AFSC) — BDS FAQ",
            "https://www.afsc.org/bds",
            "Quaker organization FAQ on boycott as nonviolent economic pressure.",
        ),
    ]

    general_resources = [
        (
            "B'Tselem",
            "https://www.btselem.org/",
            "Israeli human rights organization documenting the occupation, settlements, "
            "and violations in the West Bank and Gaza.",
        ),
        (
            "Al-Haq",
            "https://www.alhaq.org/",
            "Palestinian legal and human rights organization based in Ramallah.",
        ),
        (
            "Addameer — Prisoner Support",
            "https://www.addameer.org/",
            "Palestinian NGO focused on prisoners, administrative detention, "
            "and military court abuses.",
        ),
        (
            "Palestinian Centre for Human Rights (Gaza)",
            "https://pchrgaza.org/",
            "Gaza-based documentation of attacks, home demolitions, and "
            "violations during military operations.",
        ),
        (
            "UN OCHA oPt",
            "https://www.ochaopt.org/",
            "United Nations humanitarian data on Gaza and the West Bank "
            "(casualties, displacement, access).",
        ),
        (
            "UNRWA",
            "https://www.unrwa.org/",
            "UN agency for Palestine refugees — schools, clinics, and aid in "
            "Gaza, West Bank, Jordan, Lebanon, and Syria.",
        ),
        (
            "ICRC — Israel and the occupied territories",
            "https://www.icrc.org/en/where-we-work/middle-east/israel-and-occupied-territories",
            "International Committee of the Red Cross on detention visits, "
            "humanitarian access, and IHL.",
        ),
        (
            "Amnesty International — Israel and the OPT",
            "https://www.amnesty.org/en/location/middle-east-and-north-africa/"
            "israel-and-the-occupied-palestinian-territories/",
            "Reports, campaigns, and legal analysis on human rights in the region.",
        ),
        (
            "Human Rights Watch — Israel/Palestine",
            "https://www.hrw.org/middle-east/north-africa/israel/palestine",
            "Investigations into unlawful attacks, displacement, and accountability.",
        ),
        (
            "Decolonize Palestine",
            "https://decolonizepalestine.com/",
            "Short educational explainers on history, occupation, and common questions.",
        ),
        (
            "IMEU",
            "https://imeu.org/",
            "Institute for Middle East Understanding — fact sheets and background context.",
        ),
        (
            "The Electronic Intifada",
            "https://electronicintifada.net/",
            "News and analysis from a pro-Palestinian perspective.",
        ),
        (
            "MATW — Palestine emergency appeal",
            "https://matwproject.org/crisis-and-emergencies/palestine",
            "Donate to humanitarian relief on the ground.",
        ),
    ]

    help_actions = [
        "Read independent reporting (CPJ, B'Tselem, UN OCHA) before sharing claims.",
        "Donate to medical and refugee aid (UNRWA, MATW, Medical Aid for Palestinians).",
        "Support BDS-aligned boycotts if you choose nonviolent economic pressure.",
        "Contact elected representatives — demand arms embargoes and accountability.",
        "Amplify Palestinian and Israeli human-rights voices, not just headlines.",
        "Attend protests, write letters, and share verified documentation.",
    ]

    def _links(items: list[tuple[str, str, str]]) -> str:
        return "".join(_resource_link(n, u, b) for n, u, b in items)

    parts = [
        "<div style='line-height:1.55;'>",
        headed_title('Free Palestine', level=2, accent=accent),
        f"<p style='{_BODY}'>"
        "<b>Learn about the occupation and how to help.</b> "
        "Independent human-rights organizations, UN data, press-freedom groups, "
        "whistleblower testimony, and BDS resources. Links open in your browser. "
        "SMK does not control or endorse every article on external sites.</p>",
        f'<nav style="{_TOC}">'
        "<b>On this page</b><br>"
        '<a href="#solidarity">Solidarity</a><br>'
        '<a href="#oppression">Aspects of oppression</a><br>'
        '<a href="#journalists">Journalists &amp; press freedom</a><br>'
        '<a href="#whistleblowers">Whistleblowers &amp; testimony</a><br>'
        '<a href="#bds">BDS &amp; boycott</a><br>'
        '<a href="#resources">Human-rights resources</a><br>'
        '<a href="#help">How to help</a><br>'
        '<a href="#framing">How to talk about it</a>'
        "</nav>",
        # --- Solidarity ---
        f'<section id="solidarity" style="{_SECTION}">',
        headed_title('Solidarity & accountability', level=3, accent=accent),
        _callout(
            "info",
            "Focus on actions and systems",
            "<p>Criticism belongs on <b>government policy, military conduct, occupation, "
            "and violations of law</b> — not on ordinary civilians because of who they are.</p>"
            "<p>Israel is a state. Palestinians are a people under occupation and blockade. "
            "Discuss both in terms of <b>rights, law, and what governments do</b>.</p>",
        ),
        _phrase_list(solidarity_phrases),
        "</section>",
        # --- Oppression ---
        f'<section id="oppression" style="{_SECTION}">',
        headed_title('Aspects of oppression', level=3, accent=accent),
        f"<p style='{_BODY}'>Documented patterns reported by UN bodies, Israeli and "
        "Palestinian human-rights groups, and international courts — not an exhaustive "
        "list, but the main structural forms:</p>",
        _bullet_block(oppression_aspects),
        _callout(
            "warn",
            "Journalists under fire",
            "<p>Since October 2023, <b>dozens of journalists and media workers</b> have "
            "been killed in Gaza according to CPJ and RSF — often while reporting, "
            "sometimes with family members. Attacking the press makes it harder to "
            "document every other violation on this list. "
            '<a href="https://cpj.org/">CPJ</a> and '
            '<a href="https://rsf.org/en/region/middle-east">RSF</a> track each case '
            "and call for independent investigations.</p>",
        ),
        "</section>",
        # --- Journalists ---
        f'<section id="journalists" style="{_SECTION}">',
        headed_title('Journalists & press freedom', level=3, accent=accent),
        f"<p style='{_BODY}'>Reporting from occupied territory is dangerous. Media workers "
        "have been killed, injured, detained, and had equipment destroyed. "
        "Protecting journalists protects everyone's right to know what is happening.</p>",
        _phrase_list(
            [
                "Investigate every killing of a journalist — impunity enables further attacks.",
                "Journalists are civilians under international law; targeting them is a war crime.",
                "Press freedom is not optional in a conflict where facts are contested.",
            ]
        ),
        f"<ul style='list-style:none; margin:16px 0; padding:0;'>{_links(journalist_resources)}</ul>",
        "</section>",
        # --- Whistleblowers ---
        f'<section id="whistleblowers" style="{_SECTION}">',
        headed_title('Whistleblowers & insider testimony', level=3, accent=accent),
        f"<p style='{_BODY}'>Some of the most credible evidence comes from people "
        "inside the system — soldiers, lawyers, and researchers who risk careers "
        "and safety to publish what official narratives omit.</p>",
        _phrase_list(
            [
                "Israeli veterans (Breaking the Silence) describing orders and conduct on the ground.",
                "Human-rights field workers (B'Tselem, Al-Haq) documenting violations in real time.",
                "Investigative journalists (+972, HRW) publishing leaked documents and testimony.",
                "Legal submissions to the ICC and UN based on evidence gathered at personal risk.",
            ]
        ),
        f"<ul style='list-style:none; margin:16px 0; padding:0;'>{_links(whistleblower_resources)}</ul>",
        "</section>",
        # --- BDS ---
        f'<section id="bds" style="{_SECTION}">',
        headed_title('BDS — Boycott, Divestment, Sanctions', level=3, accent=accent),
        f"<p style='{_BODY}'>The <b>BDS movement</b> is a Palestinian-led campaign for "
        "nonviolent economic pressure, inspired by the boycott against apartheid South Africa. "
        "It asks individuals, unions, churches, and companies to withdraw support from "
        "institutions and corporations complicit in occupation and inequality.</p>",
        _phrase_list(
            [
                "Boycott — refuse to buy from companies profiting from occupation.",
                "Divestment — pull investments from those companies (pensions, universities).",
                "Sanctions — governments cut military aid and trade privileges until law is respected.",
            ]
        ),
        _callout(
            "info",
            "The three BDS demands",
            "<ol style='margin:8px 0 0 18px; padding:0;'>"
            "<li>End the occupation and dismantle the Wall.</li>"
            "<li>Equal rights for Palestinian citizens of Israel.</li>"
            "<li>Right of return for Palestinian refugees (UN Resolution 194).</li>"
            "</ol>",
        ),
        f"<ul style='list-style:none; margin:16px 0; padding:0;'>{_links(bds_resources)}</ul>",
        "</section>",
        # --- General resources ---
        f'<section id="resources" style="{_SECTION}">',
        headed_title('Human-rights resources', level=3, accent=accent),
        f"<ul style='list-style:none; margin:16px 0; padding:0;'>{_links(general_resources)}</ul>",
        "</section>",
        # --- How to help ---
        f'<section id="help" style="{_SECTION}">',
        headed_title('How to help', level=3, accent=accent),
        _phrase_list(help_actions),
        "</section>",
        # --- Framing ---
        f'<section id="framing" style="{_SECTION} border-bottom:none; padding-bottom:0;">',
        headed_title('How to talk about it', level=3, accent=accent),
        f"<p style='{_BODY}'>Name policies and conduct — occupation, blockade, settlements, "
        "journalist killings, collective punishment — without targeting civilians as a group.</p>",
        _phrase_list(
            [
                "Oppose the occupation — support Palestinian rights.",
                "Condemn unlawful settlements and collective punishment.",
                "Demand an end to the blockade of Gaza.",
                "Hold Israel accountable for violations of international law.",
                "Support investigations into war crimes by all parties.",
                "Protect journalists — their work is how the world sees what happens.",
            ]
        ),
        _callout(
            "tip",
            "Start here",
            "<p>New? <b>Decolonize Palestine</b> for explainers, <b>B'Tselem</b> for "
            "occupation docs, <b>CPJ</b> for journalist safety, <b>BDS Movement</b> for "
            "boycott guidance, <b>UN OCHA</b> for live humanitarian numbers.</p>",
        ),
        "</section>",
        "</div>",
    ]
    return "".join(parts)
