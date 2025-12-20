"""
OSS AI Village - Multi-Agent Dashboard
A responsive UI for watching LLMs collaborate on open source issues.
"""

import streamlit as st
from state import init_state
from orchestrator import run_pipeline
from config import get_model_display_name, get_model_color, LLM_MODE

# Page config
st.set_page_config(
    page_title="OSS AI Village",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better aesthetics
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    /* Agent cards */
    .agent-card {
        background: #1e1e2e;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid;
        margin-bottom: 0.5rem;
    }
    
    /* Message bubbles */
    .message-bubble {
        background: #2d2d3d;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-left: 3px solid;
    }
    
    /* Hide default streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #1e1e2e; }
    ::-webkit-scrollbar-thumb { background: #4a4a5a; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# Initialize state
if "state" not in st.session_state:
    st.session_state.state = init_state()
if "live_events" not in st.session_state:
    st.session_state.live_events = []
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False

state = st.session_state.state

# =============================================================================
# HEADER
# =============================================================================
header_col1, header_col2, header_col3 = st.columns([3, 2, 1])

with header_col1:
    st.markdown("# OSS AI Village")
    mode_text = "Remote (Colab GPU)" if LLM_MODE == "remote" else "Local (Ollama)"
    st.caption(f"Multi-agent collaboration on GitHub issues | {mode_text}")

with header_col2:
    # Status indicator
    if st.session_state.pipeline_running:
        st.markdown("### Pipeline Running...")
    elif state.get("proposed_fix"):
        st.markdown("### Fix Ready for Review")
    else:
        st.markdown("### Ready")

with header_col3:
    run_clicked = st.button("Rock 'n Roll", type="primary", use_container_width=True, disabled=st.session_state.pipeline_running)

# =============================================================================
# RUN PIPELINE (if button clicked) - BEFORE rendering columns
# =============================================================================
if run_clicked and not st.session_state.pipeline_running:
    # Set running state and rerun to show "running" status
    st.session_state.pipeline_running = True
    st.session_state.state = init_state()
    st.session_state.live_events = []
    st.rerun()

st.divider()

# =============================================================================
# MAIN LAYOUT - Three fixed columns
# =============================================================================
col_scout, col_discussion, col_result = st.columns([1, 2, 1])

# =============================================================================
# LEFT COLUMN: Scout & Issue
# =============================================================================
with col_scout:
    # Scout Agent
    st.markdown(f"### Scout")
    st.caption(f"Model: **{get_model_display_name('scout')}**")
    
    scout = state["agents"]["scout"]
    
    # Show running state if pipeline is running
    if st.session_state.pipeline_running:
        st.markdown(f"Status: :orange[running]")
        st.info("Scout is searching for issues...")
    else:
        status_color = {"idle": "gray", "running": "orange", "done": "green"}.get(scout["status"], "gray")
        st.markdown(f"Status: :{status_color}[{scout['status']}]")
        
        # Scout events in scrollable container
        if scout["events"]:
            with st.container(height=180):
                for event in reversed(scout["events"]):  # Newest first
                    with st.expander(event["step"], expanded=False):
                        st.write(event["detail"])
        else:
            st.info("Click Rock 'n Roll to start")
    
    st.divider()
    
    # Selected Issue
    st.markdown("### Selected Issue")
    
    if state["issue"]:
        issue = state["issue"]
        st.markdown(f"**{issue['repo']}**")
        st.markdown(f"#{issue['number']}: {issue['title'][:60]}...")
        
        if "score" in issue:
            score = issue["score"]
            score_color = "green" if score >= 7 else "orange" if score >= 5 else "red"
            st.markdown(f"AI Score: :{score_color}[**{score}/10**]")
        
        st.link_button("View on GitHub", issue['url'], use_container_width=True)
        
        with st.expander("Full Description"):
            st.write(issue.get("body", "No description"))
    else:
        st.info("No issue selected")

# =============================================================================
# CENTER COLUMN: Roundtable Discussion OR Live Progress
# =============================================================================
with col_discussion:
    st.markdown("### Engineer Roundtable")
    
    # Engineer badges with actual model names
    badge_cols = st.columns(3)
    engineers = [
        ("conservative", get_model_display_name("conservative"), get_model_color("conservative")),
        ("innovative", get_model_display_name("innovative"), get_model_color("innovative")),
        ("quality", get_model_display_name("quality"), get_model_color("quality"))
    ]
    
    for i, (eng_id, name, color) in enumerate(engineers):
        with badge_cols[i]:
            style_name = eng_id.capitalize()
            st.markdown(f"""
            <div style="background: {color}22; border-left: 3px solid {color}; padding: 8px; border-radius: 4px; margin-bottom: 8px;">
                <strong style="color: {color};">{name}</strong><br>
                <small style="color: #888;">{style_name}</small>
            </div>
            """, unsafe_allow_html=True)
    
    # === THIS IS WHERE THE LIVE PROGRESS OR DISCUSSION GOES ===
    if st.session_state.pipeline_running:
        # We're in running mode - execute the pipeline here
        state = st.session_state.state
        
        # Collect events during execution
        def on_event(message, event_type):
            """Callback to collect live events."""
            st.session_state.live_events.insert(0, message)  # Insert at beginning (newest first)
        
        # Show progress in a fixed container
        with st.container(height=400):
            with st.spinner("Running AI Village Pipeline..."):
                run_pipeline(state, on_event=on_event)
            
            st.success("Pipeline complete!")
            st.markdown("**Progress Log** (newest first):")
            for evt in st.session_state.live_events[:15]:  # Show last 15 events
                st.markdown(f"- {evt}")
        
        # Done - turn off running mode and rerun to show results
        st.session_state.pipeline_running = False
        st.rerun()
    else:
        # Show existing discussion or placeholder
        roundtable = state.get("roundtable", {})
        discussion = roundtable.get("discussion", [])
        
        if discussion:
            rt_status = roundtable.get("status", "idle")
            status_color = {"idle": "gray", "running": "orange", "done": "green"}.get(rt_status, "gray")
            st.markdown(f"Status: :{status_color}[{rt_status}]")
            
            # Scrollable discussion (newest first)
            with st.container(height=450):
                for msg in reversed(discussion):  # Reverse to show newest first
                    speaker = msg["speaker"]
                    message = msg["message"]
                    msg_type = msg.get("type", "message")
                    color = msg.get("color", "#666")
                    style = msg.get("style", "")
                    
                    if msg_type == "system":
                        st.markdown(f"---")
                        st.markdown(f"**{message}**")
                        st.markdown(f"---")
                    else:
                        # Create colored message bubble
                        st.markdown(f"""
                        <div style="background: #2a2a3a; border-left: 3px solid {color}; padding: 10px; border-radius: 6px; margin: 8px 0;">
                            <strong style="color: {color};">{speaker}</strong> <small style="color: #888;">({style})</small>
                            <p style="margin-top: 6px; color: #ddd; font-size: 0.9em;">{message[:500]}{'...' if len(message) > 500 else ''}</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("The roundtable will begin after Scout finds an issue")
            st.markdown("""
            **How it works:**
            1. **Round 1** - Each LLM proposes a fix
            2. **Round 2** - LLMs critique each other
            3. **Round 3** - Defense & revision
            4. **Round 4** - Vote on the best approach
            """)

# =============================================================================
# RIGHT COLUMN: Winning Fix & Human Review
# =============================================================================
with col_result:
    st.markdown("### Winning Fix")
    
    if state.get("proposed_fix"):
        fix = state["proposed_fix"]
        winner_color = fix.get("color", "#4ECDC4")
        
        # Winner card
        st.markdown(f"""
        <div style="background: {winner_color}22; border: 1px solid {winner_color}; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
            <strong style="color: {winner_color}; font-size: 1.1em;">{fix.get('engineer', 'N/A')}</strong><br>
            <small style="color: #888;">{fix.get('style', '')} approach</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Vote breakdown
        votes = fix.get("votes", {})
        vote_details = fix.get("vote_details", {})
        
        st.markdown("**Vote Results:**")
        for voter_id, vote in votes.items():
            voter_name = vote_details.get(voter_id, {}).get("voter_name", voter_id)
            st.markdown(f"- {voter_name} voted for *{vote}*")
        
        st.divider()
        
        # The actual fix code
        st.markdown("**Proposed Code:**")
        with st.container(height=200):
            st.code(fix["fix"], language="python")
        
        st.divider()
        
        # Human Review Panel
        st.markdown("### Human Review")
        
        review_col1, review_col2 = st.columns(2)
        with review_col1:
            if st.button("Approve", type="primary", use_container_width=True):
                state["proposed_fix"]["status"] = "approved"
                st.success("Fix approved! Ready for PR.")
        
        with review_col2:
            if st.button("Reject", type="secondary", use_container_width=True):
                state["proposed_fix"]["status"] = "rejected"
                st.warning("Fix rejected.")
        
        # Edit option
        with st.expander("Edit Fix"):
            edited_fix = st.text_area(
                "Modify the code:",
                value=fix["fix"],
                height=150,
                key="edit_fix"
            )
            if st.button("Save Changes"):
                state["proposed_fix"]["fix"] = edited_fix
                state["proposed_fix"]["status"] = "edited"
                st.success("Changes saved!")
                st.rerun()
        
        # Status indicator
        fix_status = fix.get("status", "pending_review")
        st.markdown(f"**Status:** {fix_status}")
        
    else:
        st.info("No fix proposed yet")
        st.markdown("""
        After the roundtable reaches consensus, you'll see:
        - The winning approach
        - Vote breakdown
        - The proposed code
        - Options to approve, reject, or edit
        """)

# =============================================================================
# FOOTER: PR Submission
# =============================================================================
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 1])

with footer_col1:
    proposed_fix = state.get("proposed_fix") if state else None
    if proposed_fix and proposed_fix.get("status") == "approved":
        st.success("Fix approved and ready for PR submission!")
        if st.button("Submit PR to GitHub", type="primary"):
            st.info("PR submission coming soon!")
    else:
        st.caption("Approve a fix to enable PR submission")

with footer_col2:
    issue_data = state.get("issue") if state else None
    issue_num = issue_data.get("number", "None") if issue_data else "None"
    st.caption(f"Issue: #{issue_num}")

with footer_col3:
    st.caption(f"Mode: {LLM_MODE.upper()}")
