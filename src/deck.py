"""Build the deck (cover plus six slides) from the saved outputs and export it to PDF.

Every number on a slide is read from a CSV in outputs/. Writes deck/qcom_nps.pptx and
deck/qcom_nps.pdf. The PDF export drives Keynote through AppleScript, so it needs a Mac with Keynote.
"""
import subprocess
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT, DECK, LOGOS = ROOT / "outputs", ROOT / "deck", ROOT / "data" / "logos"
rgb = lambda h: RGBColor.from_string(h)
RED, DARK, CARD, INK, GREY, RULE, PALE, WHITE = (rgb(h) for h in ("CC0000", "1A1A1A", "F2F2F2", "333333", "6B6B6B", "D9D9D9", "F7D6D6", "FFFFFF"))

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


def text(slide, x, y, w, h, paras, size=16, color=INK, bold=False, align=None):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    for i, t in enumerate([paras] if isinstance(paras, str) else paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after, p.alignment = Pt(8), align
        run = p.add_run()
        run.text = t
        run.font.size, run.font.bold, run.font.color.rgb = Pt(size), bold, color


def shape(slide, kind, x, y, w, h, fill):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def card(slide, x, y, w, h):
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, CARD).adjustments[0] = 0.06


def page(prs, n, kicker, title, source):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    shape(s, MSO_SHAPE.RECTANGLE, 0, 0, 0.25, 7.5, RED)
    text(s, 0.65, 0.3, 12, 0.35, kicker.upper(), size=12, color=RED, bold=True)
    text(s, 0.65, 0.62, 12.1, 1.0, title, size=24, color=DARK, bold=True)
    shape(s, MSO_SHAPE.RECTANGLE, 0.65, 1.62, 12.05, 0.03, RULE)
    text(s, 0.65, 7.05, 10.8, 0.3, source, size=10, color=GREY)
    text(s, 12.0, 7.05, 0.7, 0.3, str(n), size=10, color=GREY, align=PP_ALIGN.RIGHT)
    return s


def pic(s, name, x, y, w):
    s.shapes.add_picture(str(OUT / f"{name}.png"), Inches(x), Inches(y), width=Inches(w))


def main():
    q, m = pd.read_csv(OUT / "nps_quarterly.csv"), pd.read_csv(OUT / "nps_monthly.csv")
    cur = q[q["period"] == q["period"].max()].set_index("app").sort_values("nps", ascending=False)
    mix = pd.read_csv(OUT / "driver_mix_quarterly.csv")
    mix = mix[(mix["quarter"] == mix["quarter"].max()) & mix["share_pct"].notna()].pivot(index="driver", columns="app", values="share_pct")
    b = pd.read_csv(OUT / "bridge.csv")
    lag, lead = b.iloc[0]["term"], b.iloc[-1]["term"]
    terms = b[b["kind"] == "term"].set_index("term")
    gap, promo = b.iloc[-1]["points"] - b.iloc[0]["points"], terms.loc["promoters", "points"]
    named = terms.loc[list(WORDS)].sort_values("points", ascending=False)
    robust = pd.read_csv(OUT / "robustness.csv")
    rob = robust.iloc[-1]
    cons, kw = pd.read_csv(OUT / "tagger_consistency.csv").iloc[0], pd.read_csv(OUT / "keyword_vs_tags.csv").iloc[0]
    start = pd.Timestamp(q["period"].max())
    span = f"{start:%b} to {(start + pd.DateOffset(months=2)):%b %Y}"
    n_months, total = m["period"].nunique(), m["n"].sum()
    source = f"Source: Google Play reviews, India, English, {total:,} reviews, Jan 2025 to Sep 2026. Figures from outputs/ in the repo."
    d1, d2, d3 = named.index[:3]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    s = prs.slides.add_slide(prs.slide_layouts[6])
    shape(s, MSO_SHAPE.RECTANGLE, 8.9, 0, 4.433, 7.5, RED)
    text(s, 9.4, 0.75, 3.6, 0.4, "AT A GLANCE", size=13, color=PALE, bold=True)
    for i, (big, small) in enumerate([(f"{total:,}", "public reviews, Jan 2025 to Sep 2026"),
                                      (f"{kw['reviews']:,.0f}", "detractor reviews tagged to 8 complaint drivers"),
                                      (f"{gap:.1f} points", f"NPS gap, {lead.capitalize()} vs {lag.capitalize()}, {span}")]):
        text(s, 9.4, 1.4 + i * 1.95, 3.7, 0.9, big, size=40, color=WHITE, bold=True)
        text(s, 9.4, 2.35 + i * 1.95, 3.5, 0.8, small, size=14, color=PALE)
        if i < 2:
            shape(s, MSO_SHAPE.RECTANGLE, 9.4, 3.3 + i * 1.95, 3.4, 0.015, PALE)
    shape(s, MSO_SHAPE.RECTANGLE, 0.8, 1.0, 0.9, 0.09, RED)
    text(s, 0.8, 1.2, 7.5, 0.4, "CASE STUDY  |  QUICK COMMERCE", size=13, color=RED, bold=True)
    text(s, 0.8, 1.65, 7.9, 2.2, ["Quick-Commerce", "NPS Benchmark"], size=46, color=DARK, bold=True)
    text(s, 0.8, 3.7, 7.5, 1.2, f"What {total / 1e6:.1f} million Google Play reviews say about Blinkit, Zepto and Swiggy Instamart", size=20, color=GREY)
    text(s, 0.8, 4.85, 4, 0.3, "APPS COMPARED", size=11, color=GREY, bold=True)
    text(s, 5.6, 4.85, 3, 0.3, "DATA SOURCE", size=11, color=GREY, bold=True)
    shape(s, MSO_SHAPE.RECTANGLE, 5.2, 5.2, 0.015, 1.4, RULE)
    for x, name, label in [(0.8, "blinkit", "Blinkit"), (2.15, "zepto", "Zepto"), (3.5, "instamart", "Instamart"), (5.75, "googleplay", "Google Play")]:
        s.shapes.add_picture(str(LOGOS / f"{name}.png"), Inches(x), Inches(5.2), height=Inches(1.05))
        text(s, x - 0.1 if name != "googleplay" else x - 0.15, 6.3, 1.25, 0.3, label, size=11, color=GREY, align=PP_ALIGN.CENTER)
    text(s, 0.8, 6.85, 7.8, 0.4, "Sri Kaasyap Vepa  |  A review based NPS proxy with a 95% margin of error", size=12, color=GREY)

    s = page(prs, 2, "Executive summary", f"{lead.capitalize()} leads {lag.capitalize()} by {gap:.1f} NPS points in {span}, and "
             f"{WORDS[d1]} and {WORDS[d2]} explain {named['points'].iloc[:2].sum():.1f} of them", source)
    for i, a in enumerate(cur.index):
        x = 0.65 + i * 4.1
        card(s, x, 1.85, 3.9, 1.35)
        s.shapes.add_picture(str(LOGOS / f"{a}.png"), Inches(x + 0.2), Inches(2.05), height=Inches(0.95))
        text(s, x + 1.3, 1.92, 2.5, 0.4, f"{a.capitalize()}, {span}", size=13, color=GREY)
        text(s, x + 1.3, 2.3, 2.6, 0.8, f"{cur.loc[a, 'nps']:.1f} (±{cur.loc[a, 'moe']:.1f})", size=28, color=RED, bold=True)
    pic(s, "deck_latest", 0.65, 3.4, 6.2)
    text(s, 7.3, 3.5, 5.4, 3.4, [
        f"The {gap:.1f} point gap: {promo:.1f} from more 5 star reviews at {lead.capitalize()}, {gap - promo:.1f} from heavier complaints at {lag.capitalize()}.",
        f"Biggest complaint gaps: {WORDS[d1]} {named.loc[d1, 'points']:.1f}, {WORDS[d2]} {named.loc[d2, 'points']:.1f}, {WORDS[d3]} {named.loc[d3, 'points']:.1f} points.",
        f"The ranking holds in {int(robust['same_ranking'].sum())} of {len(robust)} quarters when 3 stars count as passive. "
        f"First place leads by {rob['lead_over_second_main']:.1f} points against ±{rob['lead_moe_main']:.1f}, so treat it as a tie."], size=16)

    bi, z = m[m["app"] != "zepto"]["nps"], m[m["app"] == "zepto"]["nps"]
    s = page(prs, 3, "NPS trend", f"Blinkit and Instamart stayed between {bi.min():.0f} and {bi.max():.0f} NPS points for {n_months} months while "
             f"Zepto swung from {z.min():.0f} to {z.max():.0f} and ended at {z.iloc[-1]:.0f}", source)
    pic(s, "deck_trend", 0.65, 1.85, 8.0)
    pic(s, "deck_gap", 8.9, 1.85, 3.8)
    text(s, 8.9, 6.15, 3.8, 0.8, "Best minus worst NPS in each quarter. The gap has not closed.", size=13, color=GREY)

    top = mix.idxmax()
    assert top["blinkit"] == top["instamart"] != top["zepto"], "the driver mix title needs rewriting"
    s = page(prs, 4, "Driver mix", f"{WORDS[top['blinkit']].capitalize()} lead the complaints at Blinkit ({mix.loc[top['blinkit'], 'blinkit']:.0f}%) and "
             f"Instamart ({mix.loc[top['blinkit'], 'instamart']:.0f}%), but {WORDS[top['zepto']]} lead at Zepto ({mix.loc[top['zepto'], 'zepto']:.0f}%)", source)
    pic(s, "deck_mix", 0.65, 1.85, 6.4)
    pic(s, "deck_heat", 7.3, 1.85, 5.4)
    text(s, 0.65, 6.45, 6.4, 0.5, f"Share of tagged detractor reviews, {span}.", size=12, color=GREY)
    text(s, 7.3, 6.45, 5.4, 0.5, "NPS points lost to each driver, per app (all reviews).", size=12, color=GREY)

    s = page(prs, 5, "Where the gap comes from", f"{lead.capitalize()}'s {gap:.1f} point lead over {lag.capitalize()} is {promo:.1f} points of 5 star reviews, "
             f"then {named.loc[d1, 'points']:.1f} from {WORDS[d1]} and {named.loc[d2, 'points']:.1f} from {WORDS[d2]}",
             f"Source: Google Play reviews, India, English, {total:,} reviews. Bars sum to the gap; driver bars carry up to ±{terms['moe'].max():.1f} points of sampling error.")
    pic(s, "waterfall", 0.9, 1.8, 11.2)

    s = page(prs, 6, "Recommendations", f"Fixing {WORDS[d1]}, {WORDS[d2]} and {WORDS[d3]} at {lag.capitalize()} is worth up to "
             f"{named['points'].iloc[:3].sum():.1f} of the {gap:.1f} NPS points to {lead.capitalize()}", source)
    for i, d in enumerate((d1, d2, d3)):
        y = 1.85 + i * 1.5
        card(s, 0.65, y, 6.6, 1.35)
        text(s, 0.8, y + 0.2, 1.7, 0.9, f"{named.loc[d, 'points']:.1f}", size=38, color=RED, bold=True)
        text(s, 2.4, y + 0.1, 4.7, 0.4, f"{i + 1}. {WORDS[d].capitalize()} (±{named.loc[d, 'moe']:.1f})", size=16, bold=True)
        text(s, 2.4, y + 0.5, 4.7, 0.8, ACTIONS[d], size=12.5)
    pic(s, "deck_stakes", 7.5, 1.85, 5.2)
    text(s, 0.65, 6.4, 12, 0.6, f"Points at stake are the extra NPS points {lag.capitalize()} loses to each driver compared with {lead.capitalize()} in {span}. "
         "Matching the leader's rate would recover them. The ± is sampling error from the tagged sample.", size=12, color=GREY)

    s = page(prs, 7, "Method and limitations", "The numbers are a review based proxy for NPS, tagged by a model and checked for consistency, not yet against human labels", source)
    text(s, 0.65, 1.8, 6.0, 0.4, "Method", size=18, color=RED, bold=True)
    text(s, 0.65, 2.3, 6.0, 4.6, [
        f"Promoter 5 stars, passive 4, detractor 1 to 3. {total:,} reviews over {n_months} months.",
        f"{kw['reviews']:,.0f} detractor reviews (1,000 per app per quarter, 4 or more words) tagged to 8 complaint drivers by Claude in an interactive session.",
        f"Two independent tagging passes agreed on {cons['agreement_pct']:.0f}% of 100 reviews (kappa {cons['kappa']:.3f}).",
        f"A keyword list agrees with the model tags on {kw['agreement_pct']:.0f}% (kappa {kw['kappa']:.2f}).",
        f"The waterfall splits the {gap:.1f} point gap exactly."], size=15)
    pic(s, "deck_validation", 6.9, 1.8, 5.8)
    text(s, 6.9, 4.45, 5.8, 0.4, "Limitations", size=18, color=RED, bold=True)
    text(s, 6.9, 4.9, 5.8, 2.1, [
        "Review based proxy, not survey NPS. Reviewers skew negative.",
        "Play Store and English only. Tags not yet checked against human labels.",
        f"Driver bars carry up to ±{terms['moe'].max():.1f} points of sampling error, and {lead.capitalize()}'s lead over second place is inside its margin."], size=13)
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
