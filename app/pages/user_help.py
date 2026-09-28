import streamlit as st

from app.components.cards import apply_custom_styles, render_user_banner

apply_custom_styles()

render_user_banner(
    title="Emergency Helplines & Safety Guidelines",
    subtitle="Direct contact directory for Tamil Nadu State Disaster Management & citizen preparedness guides.",
)

# Helplines Section
st.subheader("📞 24/7 Official Emergency Helplines")
st.caption("Tap or call these toll-free numbers directly from any phone across Tamil Nadu.")

h_col1, h_col2, h_col3 = st.columns(3)

with h_col1:
    st.markdown(
        """
        <div class="helpline-box">
            <div style="font-size: 0.9rem; font-weight: 700; color: #546E7A; text-transform: uppercase;">
                State Emergency Control
            </div>
            <div class="helpline-number">1070</div>
            <div style="font-size: 0.85rem; color: #37474F; margin-top: 0.3rem;">
                State Emergency Operations Centre (SEOC) — Chennai
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with h_col2:
    st.markdown(
        """
        <div class="helpline-box">
            <div style="font-size: 0.9rem; font-weight: 700; color: #546E7A; text-transform: uppercase;">
                District Emergency Control
            </div>
            <div class="helpline-number">1077</div>
            <div style="font-size: 0.85rem; color: #37474F; margin-top: 0.3rem;">
                District Collectorate DEOC (Connects to Local District)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with h_col3:
    st.markdown(
        """
        <div class="helpline-box">
            <div style="font-size: 0.9rem; font-weight: 700; color: #546E7A; text-transform: uppercase;">
                Medical & Ambulance
            </div>
            <div class="helpline-number" style="color: #2E7D32;">108</div>
            <div style="font-size: 0.85rem; color: #37474F; margin-top: 0.3rem;">
                24/7 Free Ambulance & Emergency Medical Support
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

h2_col1, h2_col2, h2_col3 = st.columns(3)

with h2_col1:
    st.markdown(
        """
        <div class="stat-card critical">
            <h4 style="margin: 0; color: #D32F2F;">🚒 Fire & Rescue</h4>
            <div style="font-size: 1.5rem; font-weight: 800; color: #263238; margin: 0.3rem 0;">101</div>
            <p style="margin: 0; font-size: 0.85rem; color: #546E7A;">Fire fighting, building collapse, and physical entrapment rescue.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with h2_col2:
    st.markdown(
        """
        <div class="stat-card info">
            <h4 style="margin: 0; color: #1976D2;">👮 Police Assistance</h4>
            <div style="font-size: 1.5rem; font-weight: 800; color: #263238; margin: 0.3rem 0;">100 / 112</div>
            <p style="margin: 0; font-size: 0.85rem; color: #546E7A;">Law enforcement, public safety, and traffic clearance during hazards.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with h2_col3:
    st.markdown(
        """
        <div class="stat-card warning">
            <h4 style="margin: 0; color: #F57C00;">🛡️ Specialized Support</h4>
            <div style="font-size: 1.15rem; font-weight: 800; color: #263238; margin: 0.3rem 0;">1091 &nbsp;|&nbsp; 1098</div>
            <p style="margin: 0; font-size: 0.85rem; color: #546E7A;">Women's Safety Helpline (1091) &amp; Childline Emergency (1098).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# Preparedness & Action Guides
st.subheader("🛡️ Hazard Safety & Preparedness Guidelines")

tab_flood, tab_cyclone, tab_fire, tab_earthquake, tab_kit = st.tabs(
    ["🌊 Flood Safety", "🌀 Cyclone Alert", "🔥 Fire Incident", "🏚️ Earthquake / Collapse", "🎒 Emergency Kit"]
)

with tab_flood:
    st.markdown(
        """
        ### 🌊 What to Do During Flash Floods
        - **Seek Higher Elevation Immediately:** Move to the upper floors of sturdy concrete buildings.
        - **Turn Off Utilities:** Disconnect the main electrical supply switch and gas cylinder valves before waters rise.
        - **Never Walk or Drive in Floodwaters:** Moving water of just 6 inches can sweep an adult off their feet; 1 foot can carry away a car.
        - **Avoid Contact with Water:** Flood waters can be contaminated with sewage or carry live electric charge from downed poles.
        - **Drink Only Boiled or Bottled Water:** Prevent waterborne infections (cholera, typhoid).
        """
    )

with tab_cyclone:
    st.markdown(
        """
        ### 🌀 Cyclone & Severe Weather Protocol
        - **Secure Windows & Glass:** Fasten storm shutters or affix adhesive tape across glass panes to prevent shattering.
        - **Stay Indoors During Calm:** The "eye" of the cyclone brings deceptive calm followed by violent reverse winds.
        - **Keep Fully Charged Devices:** Fully charge phones, torches, and power banks prior to landfall.
        - **Disconnect Antenna & Appliances:** Protect internal home wiring from lightning surges.
        """
    )

with tab_fire:
    st.markdown(
        """
        ### 🔥 Fire Safety & Evacuation
        - **Crawl Low Under Smoke:** Inhaling toxic smoke is the leading cause of fire fatalities. Air is cleanest near the floor.
        - **Feel Doors Before Opening:** If the handle or door feels hot, do not open it; fire is on the other side.
        - **Never Use Elevators:** Always use emergency fire exit staircases.
        - **Stop, Drop, and Roll:** If clothing catches fire, immediately stop, drop to the ground, and roll to extinguish flames.
        """
    )

with tab_earthquake:
    st.markdown(
        """
        ### 🏚️ Earthquake & Structural Collapse
        - **Drop, Cover, and Hold On:** Drop down to the floor, take cover under a sturdy desk/table, and hold on firmly.
        - **Stay Clear of Glass & Heavy Shelves:** Position away from windows, ceiling fans, and tall furniture.
        - **If Trapped:** Tap on pipes or walls with an object so rescue crews can detect sound with acoustic sensors. Cover your mouth with a cloth.
        """
    )

with tab_kit:
    st.markdown(
        """
        ### 🎒 Standard Emergency Go-Bag Essentials
        Assemble these items into a durable waterproof bag:
        1. **Drinking Water:** 3 liters per person per day (minimum 3 days supply).
        2. **Non-Perishable Food:** Energy bars, dry fruits, biscuits, infant formula.
        3. **First Aid Box:** Bandages, antiseptic lotion, ORS sachets, paracetamol, personal prescriptions.
        4. **Battery Torch & Extra Cells:** Water-resistant LED torch and radio.
        5. **Important Documents:** Aadhaar, insurance, property deeds stored in sealed ziplock bags.
        6. **Cash & Power Bank:** Fully charged high-capacity power bank and emergency cash notes.
        """
    )

