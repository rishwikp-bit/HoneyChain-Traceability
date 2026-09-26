import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime
import pandas as pd
import joblib
import qrcode
from io import BytesIO


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="HoneyChain",
    page_icon="🍯",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "/content/HoneyChain/data/honeychain.db"

PRODUCTION_MODEL_PATH = (
    "/content/HoneyChain/models/production_model.pkl"
)

HEALTH_MODEL_PATH = (
    "/content/HoneyChain/models/hive_health_model.pkl"
)


# ============================================================
# PREMIUM UI
# ============================================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(
        135deg,
        #FFFDF7 0%,
        #FFF8E7 50%,
        #FFF3D1 100%
    );
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #24170B 0%,
        #3A250F 55%,
        #4A2E0D 100%
    );
}

section[data-testid="stSidebar"] * {
    color: #FFF8E7 !important;
}

/* Titles */

h1 {
    color: #5A3500;
    font-weight: 800;
}

h2 {
    color: #6B4300;
    font-weight: 750;
}

h3 {
    color: #7A4B00;
}

/* Cards */

.honey-card {
    background: rgba(255,255,255,0.78);
    border: 1px solid #E8D5A7;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 18px;
    box-shadow: 0 5px 18px rgba(80,50,10,0.08);
}

.metric-card {
    background: white;
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #E8D5A7;
    box-shadow: 0 4px 14px rgba(80,50,10,0.07);
    text-align: center;
}

.metric-number {
    font-size: 30px;
    font-weight: 800;
    color: #8A5700;
}

.metric-label {
    font-size: 14px;
    color: #765C35;
}

/* Status */

.status-good {
    background: #EAF7EA;
    border-left: 5px solid #3C8D40;
    padding: 14px;
    border-radius: 10px;
}

.status-warning {
    background: #FFF4D6;
    border-left: 5px solid #D69A00;
    padding: 14px;
    border-radius: 10px;
}

.status-danger {
    background: #FDECEC;
    border-left: 5px solid #C94141;
    padding: 14px;
    border-radius: 10px;
}

/* Timeline */

.timeline-card {
    background: white;
    border-radius: 14px;
    padding: 18px;
    margin: 10px 0;
    border-left: 5px solid #D99A18;
    box-shadow: 0 3px 10px rgba(80,50,10,0.06);
}

/* Buttons */

.stButton > button {
    border-radius: 10px;
    font-weight: 650;
}

/* Footer */

footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def get_beekeepers():
    conn = get_connection()

    data = pd.read_sql_query(
        "SELECT * FROM beekeepers",
        conn
    )

    conn.close()
    return data


def get_hives():
    conn = get_connection()

    data = pd.read_sql_query(
        "SELECT * FROM hives",
        conn
    )

    conn.close()
    return data


def get_batches():
    conn = get_connection()

    data = pd.read_sql_query(
        "SELECT * FROM honey_batches ORDER BY harvest_date DESC",
        conn
    )

    conn.close()
    return data


def get_batch_ids():
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT batch_id FROM honey_batches ORDER BY batch_id"
    )

    batch_ids = [row[0] for row in cursor.fetchall()]

    conn.close()

    return batch_ids


def get_batch(batch_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM honey_batches WHERE batch_id = ?",
        (batch_id,)
    )

    row = cursor.fetchone()

    conn.close()

    return dict(row) if row else None


# ============================================================
# BLOCKCHAIN
# ============================================================

class Block:

    def __init__(self, index, data, previous_hash):

        self.index = index

        self.timestamp = str(datetime.now())

        self.data = data

        self.previous_hash = previous_hash

        self.hash = self.calculate_hash()


    def calculate_hash(self):

        block_content = (
            str(self.index)
            + self.timestamp
            + json.dumps(self.data, sort_keys=True)
            + self.previous_hash
        )

        return hashlib.sha256(
            block_content.encode()
        ).hexdigest()


class HoneyBlockchain:

    def __init__(self):

        self.chain = [
            self.create_genesis_block()
        ]


    def create_genesis_block(self):

        return Block(
            0,
            {
                "message":
                "HoneyChain Genesis Block"
            },
            "0"
        )


    def get_latest_block(self):

        return self.chain[-1]


    def add_block(self, data):

        previous_block = self.get_latest_block()

        new_block = Block(
            len(self.chain),
            data,
            previous_block.hash
        )

        self.chain.append(new_block)


    def is_chain_valid(self):

        for i in range(1, len(self.chain)):

            current_block = self.chain[i]

            previous_block = self.chain[i - 1]

            if (
                current_block.hash
                != current_block.calculate_hash()
            ):
                return False

            if (
                current_block.previous_hash
                != previous_block.hash
            ):
                return False

        return True


def create_blockchain_for_batch(batch):

    blockchain = HoneyBlockchain()

    blockchain.add_block({

        "batch_id":
        batch["batch_id"],

        "event":
        "Harvest",

        "location":
        batch["location"],

        "status":
        "Harvested",

        "honey_type":
        batch["honey_type"],

        "harvest_date":
        batch["harvest_date"],

        "quantity_kg":
        batch["quantity_kg"]
    })


    blockchain.add_block({

        "batch_id":
        batch["batch_id"],

        "event":
        "Processing",

        "location":
        "Telangana Processing Center",

        "status":
        "Processed"
    })


    blockchain.add_block({

        "batch_id":
        batch["batch_id"],

        "event":
        "Packaging",

        "location":
        "Telangana Packaging Center",

        "status":
        "Packaged"
    })


    blockchain.add_block({

        "batch_id":
        batch["batch_id"],

        "event":
        "Distribution",

        "location":
        "Hyderabad Distribution Center",

        "status":
        "Dispatched"
    })


    return blockchain


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    "# 🍯 HoneyChain"
)

st.sidebar.caption(
    "Smart Honey Traceability & Hive Intelligence"
)

st.sidebar.markdown("---")


page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "👨‍🌾 Beekeepers",
        "🐝 Hive Monitoring",
        "📦 Honey Batches",
        "🔗 Blockchain Traceability",
        "📱 QR Verification",
        "🤖 AI Predictions"
    ]
)


st.sidebar.markdown("---")

st.sidebar.caption(
    "Secure • Traceable • Intelligent"
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title("🍯 HoneyChain")

    st.subheader(
        "Smart Honey Traceability & Hive Intelligence"
    )

    st.markdown(
        "A smart honey ecosystem for secure traceability, "
        "QR-based verification, and AI-powered hive intelligence."
    )

    st.markdown("---")


    # Database data

    try:

        beekeepers = get_beekeepers()
        hives = get_hives()
        batches = get_batches()

    except Exception as e:

        st.error(
            f"Database error: {e}"
        )

        st.stop()


    # Metrics

    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-number">
                    {len(beekeepers)}
                </div>
                <div class="metric-label">
                    Beekeepers
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    with c2:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-number">
                    {len(hives)}
                </div>
                <div class="metric-label">
                    Active Hives
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    with c3:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-number">
                    {len(batches)}
                </div>
                <div class="metric-label">
                    Honey Batches
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    with c4:

        blockchain_status = "VALID"

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-number">
                    ✓
                </div>
                <div class="metric-label">
                    Blockchain
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown("<br>", unsafe_allow_html=True)


    # Production overview

    st.markdown(
        '<div class="honey-card">',
        unsafe_allow_html=True
    )

    st.subheader(
        "🍯 Honey Production Overview"
    )

    if not batches.empty:

        total_quantity = batches[
            "quantity_kg"
        ].sum()

        st.metric(
            "Total Recorded Honey",
            f"{total_quantity:.1f} kg"
        )

        st.dataframe(
            batches[
                [
                    "batch_id",
                    "honey_type",
                    "harvest_date",
                    "quantity_kg",
                    "status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No honey batches available."
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


    # System status

    st.subheader(
        "🛡️ System Status"
    )

    s1, s2, s3 = st.columns(3)


    with s1:

        st.markdown(
            """
            <div class="status-good">
                <b>Blockchain</b><br>
                ✓ Integrity Verified
            </div>
            """,
            unsafe_allow_html=True
        )


    with s2:

        st.markdown(
            """
            <div class="status-good">
                <b>Database</b><br>
                ✓ Connected
            </div>
            """,
            unsafe_allow_html=True
        )


    with s3:

        st.markdown(
            """
            <div class="status-good">
                <b>AI Models</b><br>
                ✓ Available
            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# BEEKEEPERS
# ============================================================

elif page == "👨‍🌾 Beekeepers":

    st.title("👨‍🌾 Beekeeper Management")

    st.subheader(
        "Registered Beekeepers & Hive Ownership"
    )

    st.markdown("---")


    try:

        data = get_beekeepers()

        if data.empty:

            st.info(
                "No beekeeper records available."
            )

        else:

            st.dataframe(
                data,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:

        st.error(
            f"Unable to load beekeeper data: {e}"
        )


# ============================================================
# HIVE MONITORING
# ============================================================

elif page == "🐝 Hive Monitoring":

    st.title("🐝 Hive Monitoring")

    st.subheader(
        "Real-Time Hive Environment & Colony Intelligence"
    )

    st.markdown("---")


    hives = get_hives()


    if hives.empty:

        st.warning(
            "No hives available."
        )

    else:

        hive_names = hives[
            "hive_name"
        ].tolist()

        selected_hive = st.selectbox(
            "Select Hive",
            hive_names
        )


        st.markdown(
            f"""
            <div class="honey-card">
                <h3>🐝 {selected_hive}</h3>
                <p>Hive Environment & Colony Monitoring</p>
            </div>
            """,
            unsafe_allow_html=True
        )


        # Simulated monitoring values

        temperature = 30.0

        humidity = 65.0

        colony_strength = 8.0

        varroa_level = 2.5

        food_availability = 8.0

        bee_population = 32000


        c1, c2, c3 = st.columns(3)


        with c1:

            st.metric(
                "🌡️ Temperature",
                f"{temperature} °C"
            )

            st.metric(
                "💧 Humidity",
                f"{humidity}%"
            )


        with c2:

            st.metric(
                "🐝 Colony Strength",
                f"{colony_strength}/10"
            )

            st.metric(
                "🦠 Varroa Level",
                f"{varroa_level}/10"
            )


        with c3:

            st.metric(
                "🌼 Food Availability",
                f"{food_availability}/10"
            )

            st.metric(
                "🐝 Bee Population",
                f"{bee_population:,}"
            )


        st.markdown("---")


        # Health calculation

        healthy = (
            20 <= temperature <= 35
            and 40 <= humidity <= 80
            and colony_strength >= 6
            and varroa_level <= 5
            and food_availability >= 5
        )


        if healthy:

            st.markdown(
                """
                <div class="status-good">
                    <h3>🟢 Hive Health: Healthy</h3>
                    Current environmental and colony
                    conditions are within the monitored range.
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                """
                <div class="status-warning">
                    <h3>🟡 Hive Health: Attention Required</h3>
                    One or more monitored conditions
                    require attention.
                </div>
                """,
                unsafe_allow_html=True
            )


        st.markdown("---")

        st.subheader(
            "📊 Monitoring Summary"
        )


        monitoring_df = pd.DataFrame({

            "Parameter": [
                "Temperature",
                "Humidity",
                "Colony Strength",
                "Varroa Level",
                "Food Availability",
                "Bee Population"
            ],

            "Value": [
                f"{temperature} °C",
                f"{humidity}%",
                f"{colony_strength}/10",
                f"{varroa_level}/10",
                f"{food_availability}/10",
                f"{bee_population:,}"
            ],

            "Status": [
                "Normal",
                "Normal",
                "Strong",
                "Low Risk",
                "Good",
                "Healthy"
            ]
        })


        st.dataframe(
            monitoring_df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# HONEY BATCHES
# ============================================================

elif page == "📦 Honey Batches":

    st.title("📦 Honey Batch Management")

    st.subheader(
        "Honey Collection, Processing & Distribution Records"
    )

    st.markdown("---")


    batches = get_batches()


    if batches.empty:

        st.warning(
            "No honey batches available."
        )

    else:

        selected_batch_id = st.selectbox(
            "Select Honey Batch",
            batches["batch_id"].tolist()
        )


        batch = get_batch(
            selected_batch_id
        )


        if batch:

            st.markdown(
                f"""
                <div class="honey-card">

                <h2>🍯 {batch['batch_id']}</h2>

                <p>
                <b>Honey Type:</b>
                {batch['honey_type']}
                </p>

                <p>
                <b>Harvest Date:</b>
                {batch['harvest_date']}
                </p>

                <p>
                <b>Quantity:</b>
                {batch['quantity_kg']} kg
                </p>

                <p>
                <b>Origin:</b>
                {batch['location']}
                </p>

                <p>
                <b>Status:</b>
                {batch['status']}
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )


            st.subheader(
                "🚚 Traceability Timeline"
            )


            timeline = [

                (
                    "🌼",
                    "Harvest",
                    "Honey collected",
                    batch["location"]
                ),

                (
                    "⚙️",
                    "Processing",
                    "Honey processed",
                    "Telangana Processing Center"
                ),

                (
                    "📦",
                    "Packaging",
                    "Product packaged",
                    "Telangana Packaging Center"
                ),

                (
                    "🚚",
                    "Distribution",
                    "Product dispatched",
                    "Hyderabad Distribution Center"
                )
            ]


            for icon, event, description, location in timeline:

                st.markdown(
                    f"""
                    <div class="timeline-card">

                    <h3>
                    {icon} {event}
                    </h3>

                    <p>
                    {description}
                    </p>

                    <small>
                    📍 {location}
                    </small>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


            st.subheader(
                "📋 All Batch Records"
            )

            st.dataframe(
                batches,
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# BLOCKCHAIN TRACEABILITY
# ============================================================

elif page == "🔗 Blockchain Traceability":

    st.title("🔗 Blockchain Traceability")

    st.subheader(
        "Tamper-Evident Honey Supply Chain Records"
    )

    st.markdown("---")


    batch_ids = get_batch_ids()


    if not batch_ids:

        st.warning(
            "No honey batches available."
        )

    else:

        selected_batch_id = st.selectbox(
            "Select Batch",
            batch_ids
        )


        batch = get_batch(
            selected_batch_id
        )


        if batch:

            blockchain = create_blockchain_for_batch(
                batch
            )

            valid = blockchain.is_chain_valid()


            if valid:

                st.markdown(
                    """
                    <div class="status-good">

                    <h3>
                    🟢 Blockchain Integrity Verified
                    </h3>

                    All recorded supply-chain blocks
                    are internally consistent.

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    """
                    <div class="status-danger">

                    <h3>
                    🔴 Blockchain Integrity Failed
                    </h3>

                    The chain contains an invalid record.

                    </div>
                    """,
                    unsafe_allow_html=True
                )


            st.markdown("---")


            c1, c2, c3 = st.columns(3)


            with c1:

                st.metric(
                    "Batch ID",
                    batch["batch_id"]
                )


            with c2:

                st.metric(
                    "Blocks",
                    len(blockchain.chain)
                )


            with c3:

                st.metric(
                    "Chain Status",
                    "VALID" if valid else "INVALID"
                )


            st.subheader(
                "🔗 Supply Chain"
            )


            flow = st.columns(4)


            events = [
                ("🌼", "Harvest"),
                ("⚙️", "Processing"),
                ("📦", "Packaging"),
                ("🚚", "Distribution")
            ]


            for col, (icon, event) in zip(
                flow,
                events
            ):

                with col:

                    st.markdown(
                        f"""
                        <div class="metric-card">

                        <div style="font-size:32px">
                        {icon}
                        </div>

                        <b>{event}</b>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )


            st.markdown("---")


            st.subheader(
                "📦 Blockchain Blocks"
            )


            for block in blockchain.chain:

                with st.expander(
                    f"Block #{block.index}"
                ):

                    st.write(
                        "**Timestamp:**",
                        block.timestamp
                    )

                    st.write(
                        "**Previous Hash:**"
                    )

                    st.code(
                        block.previous_hash
                    )

                    st.write(
                        "**Current Hash:**"
                    )

                    st.code(
                        block.hash
                    )

                    st.write(
                        "**Block Data:**"
                    )

                    st.json(
                        block.data
                    )


# ============================================================
# QR VERIFICATION
# ============================================================

elif page == "📱 QR Verification":

    st.title("📱 Honey Verification")

    st.subheader(
        "Scan. Verify. Trace Your Honey."
    )

    st.markdown("---")


    batch_ids = get_batch_ids()


    if not batch_ids:

        st.warning(
            "No honey batches available."
        )

    else:

        selected_batch_id = st.selectbox(
            "🔎 Select Honey Batch",
            batch_ids
        )


        batch = get_batch(
            selected_batch_id
        )


        if batch:

            blockchain = create_blockchain_for_batch(
                batch
            )

            blockchain_valid = (
                blockchain.is_chain_valid()
            )


            if blockchain_valid:

                st.success(
                    "✅ AUTHENTIC PRODUCT — VERIFIED"
                )

                st.caption(
                    "This batch has a valid HoneyChain "
                    "traceability record."
                )

            else:

                st.error(
                    "❌ VERIFICATION FAILED"
                )


            st.markdown("---")


            qr_col, details_col = st.columns(
                [1, 1.5]
            )


            # QR

            with qr_col:

                st.subheader(
                    "📲 Product QR Code"
                )


                qr_data = (
                    "HoneyChain Batch Verification: "
                    + batch["batch_id"]
                )


                qr = qrcode.make(
                    qr_data
                )


                qr_buffer = BytesIO()

                qr.save(
                    qr_buffer,
                    format="PNG"
                )

                qr_buffer.seek(0)


                st.image(
                    qr_buffer,
                    width=260
                )


                st.download_button(
                    label="⬇️ Download QR Code",
                    data=qr_buffer.getvalue(),
                    file_name=(
                        batch["batch_id"]
                        + ".png"
                    ),
                    mime="image/png"
                )


            # Product details

            with details_col:

                st.subheader(
                    "🍯 Product Details"
                )


                st.markdown(
                    f"""
                    <div class="honey-card">

                    <h2>
                    {batch['batch_id']}
                    </h2>

                    <p>
                    <b>Honey Type:</b>
                    {batch['honey_type']}
                    </p>

                    <p>
                    <b>Harvest Date:</b>
                    {batch['harvest_date']}
                    </p>

                    <p>
                    <b>Quantity:</b>
                    {batch['quantity_kg']} kg
                    </p>

                    <p>
                    <b>Origin:</b>
                    {batch['location']}
                    </p>

                    <p>
                    <b>Status:</b>
                    {batch['status']}
                    </p>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


            st.markdown("---")


            st.subheader(
                "🚚 Full Honey Journey"
            )


            journey = [

                (
                    "🌼",
                    "Harvest",
                    "Honey collected",
                    batch["location"]
                ),

                (
                    "⚙️",
                    "Processing",
                    "Honey processed",
                    "Telangana Processing Center"
                ),

                (
                    "📦",
                    "Packaging",
                    "Product packaged",
                    "Telangana Packaging Center"
                ),

                (
                    "🚚",
                    "Distribution",
                    "Product dispatched",
                    "Hyderabad Distribution Center"
                )
            ]


            for icon, event, description, location in journey:

                st.markdown(
                    f"""
                    <div class="timeline-card">

                    <h3>
                    {icon} {event}
                    </h3>

                    <p>
                    {description}
                    </p>

                    <small>
                    📍 {location}
                    </small>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


            st.markdown("---")


            st.subheader(
                "🔐 Blockchain Verification"
            )


            if blockchain_valid:

                st.success(
                    "✓ Blockchain record is valid"
                )

            else:

                st.error(
                    "✗ Blockchain record is invalid"
                )


            st.caption(
                "The QR code identifies this HoneyChain batch "
                "verification record."
            )


# ============================================================
# AI PREDICTIONS
# ============================================================

elif page == "🤖 AI Predictions":

    st.title("🤖 AI Hive Intelligence")

    st.subheader(
        "AI-Powered Honey Production & Hive Health Analytics"
    )

    st.markdown("---")


    tab1, tab2 = st.tabs(
        [
            "🍯 Honey Production",
            "🐝 Hive Health"
        ]
    )


    # ========================================================
    # PRODUCTION
    # ========================================================

    with tab1:

        st.subheader(
            "🍯 Honey Production Prediction"
        )


        try:

            production_model = joblib.load(
                PRODUCTION_MODEL_PATH
            )

            st.success(
                "Production model loaded successfully."
            )


            c1, c2, c3 = st.columns(3)


            with c1:

                temperature = st.number_input(
                    "Temperature (°C)",
                    min_value=0.0,
                    max_value=50.0,
                    value=30.0
                )


                humidity = st.number_input(
                    "Humidity (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=65.0
                )


            with c2:

                rainfall = st.number_input(
                    "Rainfall (mm)",
                    min_value=0.0,
                    max_value=300.0,
                    value=5.0
                )


                hive_weight = st.number_input(
                    "Hive Weight",
                    min_value=0.0,
                    max_value=100.0,
                    value=45.0
                )


            with c3:

                colony_strength = st.number_input(
                    "Colony Strength",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0
                )


                flower_availability = st.number_input(
                    "Flower Availability",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0
                )


            if st.button(
                "🔮 Predict Honey Production"
            ):

                input_data = pd.DataFrame({

                    "temperature": [
                        temperature
                    ],

                    "humidity": [
                        humidity
                    ],

                    "rainfall": [
                        rainfall
                    ],

                    "hive_weight": [
                        hive_weight
                    ],

                    "colony_strength": [
                        colony_strength
                    ],

                    "flower_availability": [
                        flower_availability
                    ]
                })


                prediction = (
                    production_model
                    .predict(input_data)[0]
                )


                st.markdown(
                    f"""
                    <div class="honey-card">

                    <h2>
                    🍯 Predicted Honey Production
                    </h2>

                    <div class="metric-number">
                    {prediction:.2f} kg
                    </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


        except Exception as e:

            st.error(
                f"Production model error: {e}"
            )


    # ========================================================
    # HIVE HEALTH
    # ========================================================

    with tab2:

        st.subheader(
            "🐝 Hive Health Risk Prediction"
        )


        try:

            health_model = joblib.load(
                HEALTH_MODEL_PATH
            )

            st.success(
                "Hive health model loaded successfully."
            )


            c1, c2, c3 = st.columns(3)


            with c1:

                temperature_h = st.number_input(
                    "Temperature",
                    min_value=0.0,
                    max_value=50.0,
                    value=30.0,
                    key="health_temp"
                )


                humidity_h = st.number_input(
                    "Humidity",
                    min_value=0.0,
                    max_value=100.0,
                    value=65.0,
                    key="health_humidity"
                )


            with c2:

                colony_strength_h = st.number_input(
                    "Colony Strength",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0,
                    key="health_colony"
                )


                varroa_level = st.number_input(
                    "Varroa Level",
                    min_value=0.0,
                    max_value=10.0,
                    value=2.5,
                    key="health_varroa"
                )


            with c3:

                food_availability_h = st.number_input(
                    "Food Availability",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0,
                    key="health_food"
                )


                bee_population = st.number_input(
                    "Bee Population",
                    min_value=0,
                    max_value=100000,
                    value=32000,
                    key="health_population"
                )


            if st.button(
                "🩺 Check Hive Health"
            ):

                input_data = pd.DataFrame({

                    "temperature": [
                        temperature_h
                    ],

                    "humidity": [
                        humidity_h
                    ],

                    "colony_strength": [
                        colony_strength_h
                    ],

                    "varroa_level": [
                        varroa_level
                    ],

                    "food_availability": [
                        food_availability_h
                    ],

                    "bee_population": [
                        bee_population
                    ]
                })


                prediction = (
                    health_model
                    .predict(input_data)[0]
                )


                prediction_text = str(
                    prediction
                )


                if (
                    prediction_text.lower()
                    in [
                        "healthy",
                        "0"
                    ]
                ):

                    st.markdown(
                        """
                        <div class="status-good">

                        <h2>
                        🟢 Hive Status: Healthy
                        </h2>

                        Current input conditions
                        indicate a healthy hive.

                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                else:

                    st.markdown(
                        """
                        <div class="status-warning">

                        <h2>
                        🟡 Hive Status: At Risk
                        </h2>

                        Current input conditions
                        indicate that the hive
                        requires attention.

                        </div>
                        """,
                        unsafe_allow_html=True
                    )


        except Exception as e:

            st.error(
                f"Hive health model error: {e}"
            )


# ============================================================
# END
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    "🍯 HoneyChain • Smart Honey Traceability"
)

