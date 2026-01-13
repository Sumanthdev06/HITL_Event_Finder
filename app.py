import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from event_agent import app

# App Configuration 
st.set_page_config(page_title="AI Event Finder", page_icon="🧡", layout="wide")

# Custom Styling (Vibrant Orange Theme) 
st.markdown("""
<style>
    /* --- Main Theme --- */
    /* Target body and .stApp to ensure full background coverage */
    body, .stApp {
        background-color: #fffaf0; /* A very light, creamy orange for the main chat area */
    }
    
    h1 {
        color: #d95f02; /* A deep, rich orange for titles */
        font-family: 'Segoe UI', sans-serif;
    }

    /* --- Sidebar & Chat Input Area Styling --- */
    [data-testid="stSidebar"], [data-testid="stChatInput"] {
        background-color: #fdbe85; /* A pleasant, sandy orange */
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] strong {
        color: #7f2704; /* A deep brown for text on the sidebar */
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #bf360c; /* A deep orange for text */
    }

    /* --- Chat Bubble Styling --- */
    /* User message - Deep contrasting orange */
    [data-testid="stChatMessage"][aria-label="user"] {
        background-color: #bf360c; /* Deep Orange */
        border-radius: 10px;
    }
    [data-testid="stChatMessage"][aria-label="user"] [data-testid="stChatMessageContent"] p {
        color: #ffffff; /* White text for user prompt */
    }

    /* Assistant message - Clean White Box */
    [data-testid="stChatMessage"][aria-label="assistant"] {
        background-color: #ffffff;
        border: 1px solid #fdcfa9; /* Light orange border */
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    }
    [data-testid="stChatMessage"][aria-label="assistant"] [data-testid="stChatMessageContent"] p {
        color: #212529; /* Dark text for readability */
    }
    
    /* --- "Agent Thinking" Box --- */
    .stExpander {
        background-color: #fff8f0 !important;
        border: 1px solid #fde4cb !important;
        border-radius: 10px !important;
    }

</style>
""", unsafe_allow_html=True)

# Sidebar 
with st.sidebar:
    st.title(" AI Event Finder")
    st.markdown("Your smart assistant for finding local events and checking the weather.")
    st.markdown("---")
    st.markdown("**How to Use:**")
    st.markdown("1. Ask for events in any city.")
    st.markdown("2. Approve or Reject the plan.")
    st.markdown("3. If you reject, provide feedback!")
    st.markdown("---")
    if st.button("Clear Conversation", use_container_width=True):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

st.title("AI Local Event Finder")

# Session State and UI Rendering 
if "messages" not in st.session_state:
    st.session_state.messages = []
if "awaiting_feedback" not in st.session_state:
    st.session_state.awaiting_feedback = False
if "agent_is_working" not in st.session_state:
    st.session_state.agent_is_working = False

# Display chat history
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        is_final = message == st.session_state.messages[-1] and not st.session_state.awaiting_feedback
        avatar = "✅" if is_final else "🤖"
        with st.chat_message("assistant", avatar=avatar):
            st.markdown(message.content)

# Agent Thinking Box 
if st.session_state.agent_is_working:
    with st.expander("🤖 Agent's Work in Progress...", expanded=True):
        last_ai_message = None
        for chunk in app.stream({"messages": st.session_state.messages}, {"recursion_limit": 100}):
            if "agent" in chunk:
                st.write("🧠 Thinking...")
                last_ai_message = chunk['agent']['messages'][-1]
            elif "action" in chunk:
                st.write("🛠️ Running Tool...")
                st.json(chunk['action']['messages'][-1].content)
            elif "human_approval" in chunk:
                st.session_state.proposed_answer = last_ai_message
                st.session_state.awaiting_feedback = True
                st.session_state.agent_is_working = False
                st.rerun()

# User Input and Approval/Feedback Forms 
if not st.session_state.agent_is_working:
    if st.session_state.awaiting_feedback is True:
        proposed_answer = st.session_state.proposed_answer
        with st.chat_message("assistant", avatar="🤖"):
            st.info("Human Review Required: Do you approve the following response?")
            st.markdown(proposed_answer.content)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve", use_container_width=True, type="primary"):
                st.session_state.messages.append(proposed_answer)
                st.session_state.awaiting_feedback = False
                st.rerun()
        with col2:
            if st.button("❌ Reject", use_container_width=True):
                st.session_state.awaiting_feedback = "rejected"
                st.rerun()
    elif st.session_state.awaiting_feedback == "rejected":
        with st.chat_message("assistant", avatar="🤖"):
            st.warning("Response rejected. Please provide feedback for improvement.")
            with st.form("feedback_form"):
                feedback = st.text_area("Your feedback:", placeholder="e.g., 'Please focus only on music events.'")
                submit_feedback = st.form_submit_button("Submit Feedback", type="primary")
            if submit_feedback and feedback:
                st.session_state.messages.append(st.session_state.proposed_answer)
                st.session_state.messages.append(HumanMessage(content=f"REJECTED. Feedback: {feedback}"))
                st.session_state.awaiting_feedback = False
                st.session_state.agent_is_working = True
                st.rerun()
    else:
        if user_query := st.chat_input("Ask about events in any city..."):
            st.session_state.messages = [HumanMessage(content=user_query)]
            st.session_state.agent_is_working = True
            st.rerun()