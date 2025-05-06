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
    line-height: 1.45;
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
    stories = {}
    for file in glob.glob(str(STORY_DIR / "*.txt")):
        name = Path(file).stem.capitalize()
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()

        # grab every {...} scene
        raw_blocks = re.findall(r'\{[\s\S]*?"id"\s*:\s*\d+[\s\S]*?\}', text)
        scenes = []
        for raw in raw_blocks:
            try:
                scenes.append(json.loads(raw))
            except json.JSONDecodeError:
                fixed = clean_block(raw)
                scenes.append(json.loads(fixed))
        scenes.sort(key=lambda s: s["id"])
        stories[name] = scenes
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
st.title("🌀 APOCALYPSE")

# === 1) ALL-PERSPECTIVE TIMELINE ============================================
if st.session_state.current_char == "All Perspectives":
    st.subheader("📆 Objective Timeline")
    for event in timeline:
        with st.expander(f"🔹 [{event['timestamp']}] **{event['title']}**"):
            st.markdown(f"**Location:** {event['location']}")
            st.markdown(f"**Characters Present:**")
            cols = st.columns(len(event["characters"]))
            for idx, char in enumerate(event["characters"]):
                with cols[idx]:
                    st.button(char, key=f"tl-{event['id']}-{char}",
                              on_click=switch_pov, args=(char, event["id"]))
            st.write(event["description"])

# === 2) SINGLE CHARACTER POV ===============================================
else:
    char = st.session_state.current_char
    scenes = stories_by_char[char]
    # header & nav back
    st.subheader(f"👁️ {char} — point of view")
    st.caption("Click any name inside a scene to jump to that character’s POV.")
    st.button("↩️ Back to master timeline", on_click=switch_pov, args=("All Perspectives", None))
    st.markdown("---")

    # optional auto-scroll to a specific scene after a jump
    jump_id = st.session_state.jump_to_scene

    for scene in scenes:
        meta = EVENT_BY_ID.get(scene["id"], {})
        label = f"[{meta.get('timestamp','')}] | {meta.get('title','Scene ' + str(scene['id']))}"

        container = st.container()
        if scene["id"] == st.session_state.jump_to_scene:
            container.markdown(f"### {label}")
        else:
            container = container.expander(label, expanded=False)

        with container:
            st.markdown(scene["content"])

            # --- jump links to other POVs -----------------
            others = meta.get("characters", [])
            if others:
                st.markdown("**Other characters in this scene:**")
                cols = st.columns(len(others))
                for i, other in enumerate(others):
                    if other == char:
                        cols[i].markdown(f"**{other}**")
                    else:
                        cols[i].button(other,
                                    key=f"{scene['id']}-{other}",
                                    on_click=switch_pov,
                                    args=(other, scene["id"]))

    # reset jump target after first render
    st.session_state.jump_to_scene = None
