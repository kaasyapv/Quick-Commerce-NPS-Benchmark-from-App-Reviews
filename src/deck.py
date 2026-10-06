"""Build the six slide deck from the saved outputs and export it to PDF.

Every number on a slide is read from a CSV in outputs/. Writes deck/qcom_nps.pptx and
deck/qcom_nps.pdf. The PDF export drives Keynote through AppleScript, so it needs a Mac with Keynote.
"""
import subprocess
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT, DECK = ROOT / "outputs", ROOT / "deck"
ACCENT, INK, GREY = RGBColor(0x1F, 0x4E, 0x79), RGBColor(0x22, 0x22, 0x22), RGBColor(0x77, 0x77, 0x77)

WORDS = {"quality_freshness": "quality and freshness", "missing_or_wrong_items": "missing or wrong items",
         "customer_support": "support and rider behaviour", "refunds_returns": "refunds and returns",
         "app_payment_bugs": "app and payment problems", "late_delivery": "late delivery",
         "fees_and_prices": "fees and prices", "out_of_stock": "out of stock or not serviceable"}
ACTIONS = {"quality_freshness": "Check expiry and condition of perishables at packing, and pull items that get repeat complaints.",
           "missing_or_wrong_items": "Add a pick and pack check, and require proof of drop before an order can be marked delivered.",
           "customer_support": "Give a human agent path after the bot, shorten the first human reply, and coach riders on conduct.",
           "refunds_returns": "Refund automatically for missing or damaged items, and publish a clear return window.",
           "app_payment_bugs": "Fix failed payment and double debit cases first, and offer cash on delivery and order cancel.",
           "late_delivery": "Show a realistic delivery time at checkout and compensate orders that run late.",
           "fees_and_prices": "Show every fee before checkout and make free cash and coupons apply the first time.",
           "out_of_stock": "Hide unavailable items and tell users early when their area is not served."}


def box(slide, x, y, w, h, paras, size=18, color=INK, bold=False):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    for i, text in enumerate([paras] if isinstance(paras, str) else paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(10)
        run = p.add_run()
        run.text = text
        run.font.size, run.font.bold, run.font.color.rgb = Pt(size), bold, color


def new_slide(prs, title, source):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout, white background
    box(s, 0.6, 0.3, 12.1, 1.2, title, size=26, color=ACCENT, bold=True)
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.5), Inches(12.1), Inches(0.04))
    rule.fill.solid()
    rule.fill.fore_color.rgb = ACCENT
    rule.line.fill.background()
    box(s, 0.6, 7.0, 12.1, 0.35, source, size=10, color=GREY)
    return s


def main():
    q, m = pd.read_csv(OUT / "nps_quarterly.csv"), pd.read_csv(OUT / "nps_monthly.csv")
    cur = q[q["period"] == q["period"].max()].set_index("app")
    mix = pd.read_csv(OUT / "driver_mix_quarterly.csv")
    mix = mix[(mix["quarter"] == mix["quarter"].max()) & mix["share_pct"].notna()].pivot(index="driver", columns="app", values="share_pct")
    b = pd.read_csv(OUT / "bridge.csv")
    lag, lead = b.iloc[0]["term"], b.iloc[-1]["term"]
    terms = b[b["kind"] == "term"].set_index("term")
    gap, promo = b.iloc[-1]["points"] - b.iloc[0]["points"], terms.loc["promoters", "points"]
    named = terms.loc[list(WORDS)].sort_values("points", ascending=False)
    rob = pd.read_csv(OUT / "robustness.csv").iloc[-1]
    cons, kw = pd.read_csv(OUT / "tagger_consistency.csv").iloc[0], pd.read_csv(OUT / "keyword_vs_tags.csv").iloc[0]
    start = pd.Timestamp(q["period"].max())
    span = f"{start:%b} to {(start + pd.DateOffset(months=2)):%b %Y}"
    n_months, total = m["period"].nunique(), m["n"].sum()
    source = f"Source: Google Play reviews, India, English, {total:,} reviews, Jan 2025 to Sep 2026; outputs/ in the repo."
    d1, d2, d3 = named.index[:3]
    top2 = named["points"].iloc[:2].sum()
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    s = new_slide(prs, f"{lead.capitalize()} leads {lag.capitalize()} by {gap:.1f} NPS points in {span}, and "
                       f"{WORDS[d1]} and {WORDS[d2]} explain {top2:.1f} of them", source)
    box(s, 0.6, 1.8, 12.1, 5, [
        f"NPS proxy, {span}: " + ", ".join(f"{a.capitalize()} {cur.loc[a, 'nps']:.1f} (±{cur.loc[a, 'moe']:.1f})" for a in cur.sort_values("nps", ascending=False).index) + ".",
        f"Of the {gap:.1f} point gap, {promo:.1f} comes from {lead.capitalize()}'s higher share of 5 star reviews and {gap - promo:.1f} from {lag.capitalize()}'s heavier detractor complaints.",
        f"The biggest complaint gaps are {WORDS[d1]} ({named.loc[d1, 'points']:.1f} points), {WORDS[d2]} ({named.loc[d2, 'points']:.1f}) and {WORDS[d3]} ({named.loc[d3, 'points']:.1f}).",
        f"The app ranking is the same in {int((pd.read_csv(OUT / 'robustness.csv')['same_ranking']).sum())} of {len(pd.read_csv(OUT / 'robustness.csv'))} quarters when 3 star reviews count as passive. "
        f"The first place lead over second is only {rob['lead_over_second_main']:.1f} points against a ±{rob['lead_moe_main']:.1f} margin, so treat it as a tie."], size=22)

    bi = m[m["app"] != "zepto"]["nps"]
    z = m[m["app"] == "zepto"]["nps"]
    s = new_slide(prs, f"Blinkit and Instamart stayed between {bi.min():.0f} and {bi.max():.0f} NPS points for {n_months} months while "
                       f"Zepto swung from {z.min():.0f} to {z.max():.0f} and ended at {z.iloc[-1]:.0f}", source)
    s.shapes.add_picture(str(OUT / "nps_trend.png"), Inches(1.4), Inches(1.7), width=Inches(10.4))

    top = mix.idxmax()
    assert top["blinkit"] == top["instamart"] != top["zepto"], "the driver mix title needs rewriting"
    s = new_slide(prs, f"{WORDS[top['blinkit']].capitalize()} lead the complaints at Blinkit ({mix.loc[top['blinkit'], 'blinkit']:.0f}%) and "
                       f"Instamart ({mix.loc[top['blinkit'], 'instamart']:.0f}%), but {WORDS[top['zepto']]} lead at Zepto ({mix.loc[top['zepto'], 'zepto']:.0f}%)", source)
    s.shapes.add_picture(str(OUT / "driver_mix_latest.png"), Inches(0.6), Inches(1.7), width=Inches(8.6))
    box(s, 9.5, 2.0, 3.4, 4.5, ["Top three complaints by share of tagged detractors"] + [
        f"{a.capitalize()}: " + ", ".join(f"{WORDS[d]} {mix.loc[d, a]:.0f}%" for d in mix.loc[list(WORDS), a].nlargest(3).index)
        for a in cur.sort_values("nps", ascending=False).index], size=15)

    s = new_slide(prs, f"{lead.capitalize()}'s {gap:.1f} point lead over {lag.capitalize()} is {promo:.1f} points of 5 star reviews, "
                       f"then {named.loc[d1, 'points']:.1f} from {WORDS[d1]} and {named.loc[d2, 'points']:.1f} from {WORDS[d2]}", source)
    s.shapes.add_picture(str(OUT / "waterfall.png"), Inches(0.9), Inches(1.7), width=Inches(11.5))

    s = new_slide(prs, f"Fixing {WORDS[d1]}, {WORDS[d2]} and {WORDS[d3]} at {lag.capitalize()} is worth up to "
                       f"{named['points'].iloc[:3].sum():.1f} of the {gap:.1f} NPS points to {lead.capitalize()}", source)
    for i, d in enumerate((d1, d2, d3)):
        x = 0.6 + i * 4.1
        box(s, x, 1.9, 3.9, 1, f"{named.loc[d, 'points']:.1f} points", size=44, color=ACCENT, bold=True)
        box(s, x, 3.0, 3.9, 0.6, f"{WORDS[d].capitalize()} (±{named.loc[d, 'moe']:.1f})", size=20, bold=True)
        box(s, x, 3.8, 3.9, 2, f"{i + 1}. {ACTIONS[d]}", size=17)
    box(s, 0.6, 6.1, 12.1, 0.8, f"Points at stake are the extra NPS points {lag.capitalize()} loses to each driver compared with {lead.capitalize()} in {span}. "
                                 "Matching the leader's rate would recover them. The ± is sampling error from the tagged sample.", size=13, color=GREY)

    s = new_slide(prs, "The numbers are a review based proxy for NPS, tagged by a model and checked for consistency, not yet against human labels", source)
    box(s, 0.6, 1.75, 6.0, 0.6, "Method", size=22, color=ACCENT, bold=True)
    box(s, 6.9, 1.75, 5.8, 0.6, "Limitations", size=22, color=ACCENT, bold=True)
    box(s, 0.6, 2.45, 6.0, 4.4, [
        f"* Promoter 5 stars, passive 4, detractor 1 to 3. {total:,} reviews, {n_months} months.",
        f"* {kw['reviews']:,.0f} detractor reviews (1,000 per app per quarter, 4 or more words) tagged to 8 complaint drivers by Claude in an interactive session.",
        f"* Two independent tagging passes agreed on {cons['agreement_pct']:.0f}% of 100 reviews (kappa {cons['kappa']:.3f}).",
        f"* A keyword baseline agrees with the model tags on {kw['agreement_pct']:.0f}% (kappa {kw['kappa']:.2f})."], size=16)
    box(s, 6.9, 2.45, 5.8, 4.4, [
        "* Review based proxy, not survey NPS. Reviewers skew negative, so levels are not comparable with published NPS.",
        "* Play Store and English only.",
        "* Agreement between tagging passes shows the rules are clear, not that the tags are right.",
        f"* Driver bars carry up to ±{terms['moe'].max():.1f} points of sampling error. {lead.capitalize()}'s lead over second place is inside its margin."], size=16)
    prs.save(DECK / "qcom_nps.pptx")
    print(f"saved {DECK / 'qcom_nps.pptx'}")


def export_pdf():
    pptx, pdf = DECK / "qcom_nps.pptx", DECK / "qcom_nps.pdf"
    script = f'''tell application "Keynote Creator Studio"
    set doc to open POSIX file "{pptx}"
    export doc to POSIX file "{pdf}" as PDF
    close doc saving no
end tell'''
    subprocess.run(["osascript", "-e", script], check=True)
    print(f"saved {pdf}")


if __name__ == "__main__":
    DECK.mkdir(exist_ok=True)
    main()
    export_pdf()
