import streamlit as st
import json, os, glob, re
from pathlib import Path

# 1)  Inject styling here
def local_css(css: str):
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

local_css("""
html, body, [class*="css"]  {
    font-family: 'EB Garamond', serif !important;
    font-size: 14px;          /* <<—  make everything smaller */
    line-height: 1.4;
}
""")

STORY_DIR = Path("stories")            # folder with aurora.txt, ethan.txt, …
TIMELINE_FILE = "story.txt"            # objective events

# ---------- Helpers ----------------------------------------------------------
@st.cache_data
def load_timeline():
    with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    
timeline = load_timeline()
# fast lookup by id
EVENT_BY_ID = {ev["id"]: ev for ev in timeline}

def character_dropdown(char_list, key_prefix, scene_id=None):
    """
    Render a dropdown and immediately switch POV on first pick.
    """
    dd_key = f"{key_prefix}-dd"

    def _jump():
        choice = st.session_state[dd_key]
        if choice and choice != "— pick —":
            switch_pov(choice, scene_id)

    st.selectbox(
        "**Jump to a character’s POV:**",
        ["— pick —"] + char_list,
        key=dd_key,
        on_change=_jump    # fires after the *first* selection
    )

def clean_block(block: str) -> str:
    """
    Make a scene block valid JSON:
    • collapse raw new-lines inside the content string into \n
    • escape any interior double-quotes
    """
    def _fix(match):
        body = match.group(1)
        body = body.replace('\\', '\\\\')        # escape backslashes first
        body = body.replace('"', r'\"')          # escape quotes
        body = body.replace('\n', r'\n')         # escape newlines
        return f'"content": "{body}"'

    # replace the whole content string
    block = re.sub(r'"content"\s*:\s*"(.*?)"', _fix, block, flags=re.S)
    return block

def load_character_stories():
    """
    Returns {Character: [segment, …]} where each segment is either
      • {"id": 4, "title": …, "content": … }  ← a JSON scene
      • {"type": "text", "content": "raw narrative"} ← plain paragraphs
    Order is preserved exactly as in the .txt file.
    """
    stories = {}
    block_pattern = re.compile(r'(\{[\s\S]*?"id"\s*:\s*\d+[\s\S]*?\})')

    for file in glob.glob(str(STORY_DIR / "*.txt")):
        name = Path(file).stem.capitalize()
        with open(file, "r", encoding="utf-8") as f:
            raw_text = f.read()

        parts = block_pattern.split(raw_text)
        segments = []

        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.startswith("{") and '"id"' in part:
                try:
                    segments.append(json.loads(part))
                except json.JSONDecodeError:
                    segments.append(json.loads(clean_block(part)))
            else:
                # plain narrative text
                segments.append({"type": "text", "content": part})

        stories[name] = segments
    return stories


timeline = load_timeline()
stories_by_char = load_character_stories()

all_characters = sorted(stories_by_char.keys())

# ---------- Session state for POV & scene -----------------------------------
if "current_char" not in st.session_state:
    st.session_state.current_char = "All Perspectives"
if "jump_to_scene" not in st.session_state:
    st.session_state.jump_to_scene = None

# ---------- Sidebar POV selector --------------------------------------------
st.sidebar.header("🔍 Select a Perspective")
selected = st.sidebar.selectbox(
    "Character POV",
    ["All Perspectives"] + all_characters,
    index=(["All Perspectives"] + all_characters).index(st.session_state.current_char)
)
st.session_state.current_char = selected

# ---------- Convenience callback --------------------------------------------
def switch_pov(char_name, scene_id=None):
    st.session_state.current_char = char_name
    st.session_state.jump_to_scene = scene_id

# ---------- MAIN VIEW --------------------------------------------------------
st.title("💥 APOCALYPSE")
st.warning("This collage apocalypse is a fictional world with many intersecting storylines, built based on real responses from random strangers we interviewed about the apocalypse. You can choose your own character to read their perspective, and also hop between characters' storylines at intersecting events.")

# === 1) ALL-PERSPECTIVE TIMELINE ============================================
if st.session_state.current_char == "All Perspectives":
    st.subheader("📆 Objective Timeline")
    for event in timeline:
        with st.expander(f"🌀 [{event['timestamp']}] **{event['title']}**"):
            st.markdown(f"**Location:** {event['location']}")
            character_dropdown(event["characters"], key_prefix=f"tl-{event['id']}",
                            scene_id=event["id"])
            st.write(f"**Summary:** {event["description"]}")

# === 2) SINGLE CHARACTER POV ===============================================
else:
    char = st.session_state.current_char
    scenes = stories_by_char[char]
    # header & nav back
    st.subheader(f"👁️ {char}'s POV")
    st.caption("Click any name inside a scene to jump to that character’s POV.")
    st.button("↩️ Back to master timeline", on_click=switch_pov, args=("All Perspectives", None))
    # st.markdown("---")

    # optional auto-scroll to a specific scene after a jump
    jump_id = st.session_state.jump_to_scene

    for seg in scenes:
        if "id" not in seg:                     # plain narrative
            st.markdown(seg["content"])
            continue

        # ---------- it's a scene ----------
        meta = EVENT_BY_ID.get(seg["id"], {})
        label = f"[{meta.get('timestamp','')}] **{meta.get('title','Scene ' + str(seg['id']))}**"

        container = st.container()
        if seg["id"] == st.session_state.jump_to_scene:
            container.info("➡️ *You are here:*")
            container.markdown(f"### {label}")
        else:
            container = container.expander(label, expanded=False)

        with container:
            st.markdown(seg["content"])

            # jump links
            others = meta.get("characters", [])
            if others and len(others) > 1:
                character_dropdown(
                    [c for c in others if c != char],
                    key_prefix=f"sc-{seg['id']}",
                    scene_id=seg["id"]
                )

    # reset jump target after first render
    st.session_state.jump_to_scene = None
