"""Write standalone HTML previews of the stage and the coin (no Streamlit or backend needed):  python -m ui.preview
Open the files in any browser to look at the scenes, or use them for screenshots in the thesis."""
import os

from ui.stage import coin_html, stage_html


def write(out="ui/preview"):
    os.makedirs(out, exist_ok=True)
    files = {
        "stage_your_turn.html": stage_html("proponent", "you", 2, "Social media should be banned for children under 16.", "Warm applause.", bubble_ai="Banning is too blunt: what about the benefits?"),
        "stage_ai_speaking.html": stage_html("opponent", "ai", 1, "Remote learning is more effective than classroom learning.", "", bubble_ai="I will challenge your evidence…"),
        "stage_ovation.html": stage_html("proponent", "you", 3, "Governments should regulate generative AI.", "Standing ovation!"),
        "coin_idle.html": coin_html(None),
        "coin_heads.html": coin_html("heads"),
        "coin_tails.html": coin_html("tails"),
    }
    for name, body in files.items():
        with open(f"{out}/{name}", "w", encoding="utf-8") as f:
            f.write(f"<!doctype html><meta charset='utf-8'>{body}")
    return list(files)


if __name__ == "__main__":
    print("wrote", ", ".join(write()))
