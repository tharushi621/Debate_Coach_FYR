import streamlit as st
from ui import ctx
from ui.views.home import roadmap_block

def render():
    st.markdown('<div class="eyebrow">How it works</div><h1 style="margin:.1em 0">From a topic to a stronger argument.</h1>'
                '<p class="sub">Every debate runs the same nine-stage loop. Open any stage for the details.</p>', unsafe_allow_html=True)
    roadmap_block(current=0, selected=0)
    st.markdown("""<div class="gl" style="margin-top:16px"><h3>What the AI does — and doesn’t</h3>
<div class="rule"><div class="k">1</div><div><b>Analyses</b> your argument with the Toulmin model (claim, evidence, warrant…).</div></div>
<div class="rule"><div class="k">2</div><div><b>Scores</b> seven dimensions from 1 to 5 and names your weakest one with a transparent rule.</div></div>
<div class="rule"><div class="k">3</div><div><b>Responds</b> to that weakness, so the next counterargument is aimed where you need practice.</div></div>
<div class="rule"><div class="k">!</div><div><b>It is not a judge.</b> There is no win or loss — you compare with your own previous debates.</div></div></div>""", unsafe_allow_html=True)
    if st.button("Start Your Debate Journey →", type="primary", key="how_cta"):
        ctx.go("debate" if ctx.me() else "auth")