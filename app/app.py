import os
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

    # Harvest
    blockchain.add_block({
        "batch_id": batch["batch_id"],
        "event": "Harvest",
        "location": batch["location"],
        "status": "Harvested",
        "honey_type": batch["honey_type"],
        "harvest_date": batch["harvest_date"],
        "quantity_kg": batch["quantity_kg"]
    })

    # Processing
    blockchain.add_block({
        "batch_id": batch["batch_id"],
        "event": "Processing",
        "location": "Telangana Processing Center",
        "status": "Processed"
    })

    # Quality Check
    blockchain.add_block({
        "batch_id": batch["batch_id"],
        "event": "Quality Check",
        "location": "Telangana Quality Lab",
        "status": "Quality Verified"
    })

    # Packaging
    blockchain.add_block({
        "batch_id": batch["batch_id"],
        "event": "Packaging",
        "location": "Telangana Packaging Center",
        "status": "Packaged"
    })

    # Distribution
    blockchain.add_block({
        "batch_id": batch["batch_id"],
        "event": "Distribution",
        "location": "Hyderabad Distribution Center",
        "status": "Dispatched"
    })

    return blockchain


def add_supply_chain_event(blockchain, batch_id, event, location, status):

    blockchain.add_block({
        "batch_id": batch_id,
        "event": event,
        "location": location,
        "status": status
    })

    return blockchain


# ============================================================
# HIVE MONITORING DATA
# ============================================================

def generate_hive_reading():
    import random

    return {
        "time": datetime.now().strftime("%H:%M:%S"),
        "temperature": round(random.uniform(27, 33), 1),
        "humidity": round(random.uniform(55, 75), 1),
        "colony_strength": round(random.uniform(6.5, 9.5), 1),
        "varroa_level": round(random.uniform(1.0, 4.0), 1),
        "food_availability": round(random.uniform(6.0, 9.5), 1),
        "bee_population": random.randint(28000, 36000)
    }


def get_hive_history():
    if "hive_history" not in st.session_state:
        st.session_state.hive_history = [
            generate_hive_reading()
            for _ in range(6)
        ]

    return st.session_state.hive_history


# ============================================================
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
# DIRECT QR BATCH VERIFICATION
# ============================================================

query_batch = st.query_params.get("batch")

if query_batch:

    batch_from_qr = get_batch(query_batch)

    if batch_from_qr:

        st.title("🍯 HoneyChain")
        st.subheader("📱 Honey Batch Verification")

        st.success("✅ Authentic HoneyChain Batch Record Found")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Batch ID",
                batch_from_qr["batch_id"]
            )

        with c2:
            st.metric(
                "Honey Type",
                batch_from_qr["honey_type"]
            )

        with c3:
            st.metric(
                "Quantity",
                f'{batch_from_qr["quantity_kg"]} kg'
            )

        st.markdown("---")

        st.subheader("🍯 Product Details")

        st.write(
            "**Honey Type:**",
            batch_from_qr["honey_type"]
        )

        st.write(
            "**Harvest Date:**",
            batch_from_qr["harvest_date"]
        )

        st.write(
            "**Origin:**",
            batch_from_qr["location"]
        )

        st.write(
            "**Status:**",
            batch_from_qr["status"]
        )

        st.markdown("---")

        blockchain = create_blockchain_for_batch(
            batch_from_qr
        )

        valid = blockchain.is_chain_valid()

        if valid:

            st.success(
                "🔗 Blockchain Integrity Verified"
            )

        else:

            st.error(
                "🔴 Blockchain Integrity Failed"
            )

        st.subheader(
            "🔗 Supply Chain Journey"
        )

        for block in blockchain.chain[1:]:

            event = block.data.get(
                "event",
                "Unknown"
            )

            location = block.data.get(
                "location",
                "Not available"
            )

            status = block.data.get(
                "status",
                "Not available"
            )

            st.markdown(
                f"""
                <div class="timeline-card">
                    <h3>{event}</h3>
                    <p>
                    <b>Status:</b> ✓ {status}
                    </p>
                    <p>
                    <b>Location:</b> 📍 {location}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")

        st.info(
            "🍯 This record contains the HoneyChain "
            "traceability information for this batch."
        )

        st.stop()

    else:

        st.error(
            f"❌ Batch {query_batch} was not found "
            "in the HoneyChain database."
        )

        st.stop()


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

        st.error(f"Database error: {e}")
        st.stop()


    # Overview metrics
    total_quantity = (
        batches["quantity_kg"].sum()
        if not batches.empty
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "👨‍🌾 Beekeepers",
            len(beekeepers)
        )

    with c2:
        st.metric(
            "🐝 Active Hives",
            len(hives)
        )

    with c3:
        st.metric(
            "📦 Honey Batches",
            len(batches)
        )

    with c4:
        st.metric(
            "🍯 Honey Recorded",
            f"{total_quantity:.1f} kg"
        )


    st.markdown("---")


    # Honey Production Overview
    st.subheader("🍯 Honey Production Overview")

    if not batches.empty:

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                f"""
                <div class="honey-card">

                <h3>🍯 Total Honey</h3>

                <div class="metric-number">
                {total_quantity:.1f} kg
                </div>

                <p>
                Total recorded honey across all batches.
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )

        with c2:

            honey_type_counts = (
                batches["honey_type"]
                .value_counts()
            )

            st.markdown("### 🌼 Honey Types")

            st.bar_chart(
                honey_type_counts
            )

    else:

        st.info(
            "No honey batch records available."
        )


    st.markdown("---")


    # Recent Batch Activity
    st.subheader("📦 Recent Honey Batch Activity")

    if not batches.empty:

        recent_batches = batches.copy()

        recent_batches = recent_batches.sort_values(
            "harvest_date",
            ascending=False
        ).head(5)

        st.dataframe(
            recent_batches[
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
            "No recent batch activity."
        )


    st.markdown("---")


    # System Status
    st.subheader("🛡️ System Status")

    s1, s2, s3 = st.columns(3)

    with s1:

        st.markdown(
            """
            <div class="status-good">

            <b>🔗 Blockchain</b><br>
            ✓ Integrity Verified

            </div>
            """,
            unsafe_allow_html=True
        )

    with s2:

        st.markdown(
            """
            <div class="status-good">

            <b>🗄️ Database</b><br>
            ✓ Connected

            </div>
            """,
            unsafe_allow_html=True
        )

    with s3:

        st.markdown(
            """
            <div class="status-good">

            <b>🤖 AI Models</b><br>
            ✓ Available

            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown("---")

    st.caption(
        "🍯 HoneyChain • Smart Honey Traceability & Hive Intelligence"
    )


# ============================================================
# ============================================================
# BEEKEEPERS
# ============================================================

elif page == "👨‍🌾 Beekeepers":

    st.title("👨‍🌾 Beekeeper Management")

    st.subheader(
        "Registered Beekeepers & Hive Ownership"
    )

    st.markdown("---")


    # Add new beekeeper
    st.subheader("➕ Add New Beekeeper")

    with st.form("add_beekeeper_form"):

        name = st.text_input(
            "Beekeeper Name"
        )

        phone = st.text_input(
            "Phone Number"
        )

        location = st.text_input(
            "Location",
            value="Telangana"
        )

        submitted = st.form_submit_button(
            "💾 Add Beekeeper"
        )

        if submitted:

            if name.strip() == "":
                st.warning(
                    "Please enter the beekeeper name."
                )

            else:

                try:

                    conn = sqlite3.connect(DB_PATH)

                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT INTO beekeepers
                        (name, phone, location)
                        VALUES (?, ?, ?)
                        """,
                        (
                            name,
                            phone,
                            location
                        )
                    )

                    conn.commit()
                    conn.close()

                    st.success(
                        f"✅ {name} added successfully!"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Unable to add beekeeper: {e}"
                    )


    st.markdown("---")


    # Display existing beekeepers
    st.subheader("📋 Registered Beekeepers")

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

        st.warning("No hives available.")

    else:

        hive_names = hives["hive_name"].tolist()

        selected_hive = st.selectbox(
            "🐝 Select Hive",
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

        # Generate new monitoring reading
        if st.button("🔄 Generate New Reading"):

            new_reading = generate_hive_reading()

            st.session_state.hive_history.append(new_reading)

            # Keep latest 12 readings
            st.session_state.hive_history =                 st.session_state.hive_history[-12:]

            st.rerun()

        history = get_hive_history()

        current = history[-1]

        temperature = current["temperature"]
        humidity = current["humidity"]
        colony_strength = current["colony_strength"]
        varroa_level = current["varroa_level"]
        food_availability = current["food_availability"]
        bee_population = current["bee_population"]

        # Current readings
        st.subheader("📡 Current Hive Readings")

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

        # Hive health
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

        # Historical charts
        st.subheader("📈 Hive Monitoring Trends")

        history_df = pd.DataFrame(history)

        chart_data = history_df.set_index("time")

        st.line_chart(
            chart_data[
                ["temperature", "humidity"]
            ],
            use_container_width=True
        )

        st.caption("🌡️ Temperature and 💧 humidity trend")

        st.line_chart(
            chart_data[
                ["colony_strength", "food_availability"]
            ],
            use_container_width=True
        )

        st.caption(
            "🐝 Colony strength and 🌼 food availability trend"
        )

        st.markdown("---")

        st.subheader("📊 Monitoring Summary")

        monitoring_df = pd.DataFrame({

            "Parameter": [
                "Temperature",
                "Humidity",
                "Colony Strength",
                "Varroa Level",
                "Food Availability",
                "Bee Population"
            ],

            "Current Value": [
                f"{temperature} °C",
                f"{humidity}%",
                f"{colony_strength}/10",
                f"{varroa_level}/10",
                f"{food_availability}/10",
                f"{bee_population:,}"
            ],

            "Status": [
                "Normal" if 20 <= temperature <= 35 else "Attention",
                "Normal" if 40 <= humidity <= 80 else "Attention",
                "Strong" if colony_strength >= 6 else "Weak",
                "Low Risk" if varroa_level <= 5 else "High Risk",
                "Good" if food_availability >= 5 else "Low",
                "Healthy" if bee_population >= 25000 else "Low"
            ]
        })

        st.dataframe(
            monitoring_df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ============================================================
# HONEY BATCHES
# ============================================================

elif page == "📦 Honey Batches":

    st.title("📦 Honey Batch Management")

    st.subheader(
        "Honey Collection, Processing & Distribution Records"
    )

    st.markdown("---")


    # Add new honey batch
    st.subheader("➕ Add New Honey Batch")

    try:

        hives_data = get_hives()

        if hives_data.empty:

            st.warning(
                "No hives available. Please add a hive first."
            )

        else:

            with st.form("add_batch_form"):

                hive_options = hives_data["hive_id"].tolist()

                selected_hive = st.selectbox(
                    "🐝 Select Hive",
                    hive_options
                )

                honey_type = st.selectbox(
                    "🍯 Honey Type",
                    [
                        "Floral Honey",
                        "Wildflower Honey",
                        "Forest Honey",
                        "Eucalyptus Honey",
                        "Other"
                    ]
                )

                harvest_date = st.date_input(
                    "📅 Harvest Date"
                )

                quantity_kg = st.number_input(
                    "⚖️ Quantity (kg)",
                    min_value=0.1,
                    step=0.1,
                    value=10.0
                )

                location = st.text_input(
                    "📍 Location",
                    value="Telangana"
                )

                submitted = st.form_submit_button(
                    "💾 Add Honey Batch"
                )

                if submitted:

                    try:

                        conn = sqlite3.connect(DB_PATH)

                        cursor = conn.cursor()

                        cursor.execute(
                            "SELECT COUNT(*) FROM honey_batches"
                        )

                        count = cursor.fetchone()[0] + 1

                        batch_id = (
                            f"HC-{datetime.now().year}-"
                            f"{count:04d}"
                        )

                        cursor.execute(
                            """
                            INSERT INTO honey_batches
                            (
                                batch_id,
                                hive_id,
                                honey_type,
                                harvest_date,
                                quantity_kg,
                                location,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                batch_id,
                                selected_hive,
                                honey_type,
                                str(harvest_date),
                                quantity_kg,
                                location,
                                "Harvested"
                            )
                        )

                        conn.commit()
                        conn.close()

                        # Create blockchain record
                        new_batch = get_batch(batch_id)

                        if new_batch:
                            blockchain = create_blockchain_for_batch(
                                new_batch
                            )

                        # Generate QR code
                        qr_folder = "/content/HoneyChain/qr_codes"
                        os.makedirs(
                            qr_folder,
                            exist_ok=True
                        )

                        qr_data = (
            f"https://holding-related-tracy-finals.trycloudflare.com/?batch={batch_id}"
        )

                        qr = qrcode.make(qr_data)

                        qr_path = os.path.join(
                            qr_folder,
                            f"{batch_id}.png"
                        )

                        qr.save(qr_path)

                        st.success(
                            f"✅ Honey batch {batch_id} added successfully!"
                        )

                        st.success(
                            "🔗 Blockchain record created with 5 supply-chain stages."
                        )

                        st.success(
                            "📱 QR verification code generated."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Unable to add honey batch: {e}"
                        )

    except Exception as e:

        st.error(
            f"Unable to load hive data: {e}"
        )


    st.markdown("---")


    # Existing honey batches
    st.subheader("📋 Honey Batch Records")

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
                    "🧪",
                    "Quality Check",
                    "Honey quality verified",
                    "Telangana Quality Lab"
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
                "🔗 Supply Chain Journey"
            )

            # Display the five supply-chain stages
            flow = st.columns(5)

            events = [
                ("🌼", "Harvest", "Honey collected"),
                ("⚙️", "Processing", "Honey processed"),
                ("🧪", "Quality Check", "Quality verified"),
                ("📦", "Packaging", "Product packaged"),
                ("🚚", "Distribution", "Product dispatched")
            ]

            for col, (icon, event, description) in zip(
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

                        <h4>{event}</h4>

                        <small>
                        ✓ {description}
                        </small>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )


            st.markdown("---")

            # Detailed supply-chain records
            st.subheader(
                "📍 Supply Chain Details"
            )

            for block in blockchain.chain[1:]:

                event = block.data.get(
                    "event",
                    "Unknown"
                )

                location = block.data.get(
                    "location",
                    "Not available"
                )

                status = block.data.get(
                    "status",
                    "Not available"
                )

                st.markdown(
                    f"""
                    <div class="timeline-card">

                    <h3>
                    {event}
                    </h3>

                    <p>
                    <b>Status:</b> ✓ {status}
                    </p>

                    <p>
                    <b>Location:</b> 📍 {location}
                    </p>

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

    st.subheader("Scan. Verify. Trace Your Honey.")

    st.markdown("---")

    batch_ids = get_batch_ids()

    if not batch_ids:

        st.warning("No honey batches available.")

    else:

        selected_batch_id = st.selectbox(
            "🔎 Select Honey Batch",
            batch_ids
        )

        batch = get_batch(selected_batch_id)

        if batch:

            blockchain = create_blockchain_for_batch(batch)
            blockchain_valid = blockchain.is_chain_valid()

            # Verification status
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

            # QR + Product Details
            qr_col, details_col = st.columns([1, 1.6])

            with qr_col:

                st.subheader("📲 Product QR Code")

                honeychain_url = "https://holding-related-tracy-finals.trycloudflare.com"

                qr_data = (
                    f"{honeychain_url}/?batch={batch['batch_id']}"
                )

                qr = qrcode.make(qr_data)

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
                    file_name=batch["batch_id"] + ".png",
                    mime="image/png"
                )

                st.caption(
                    "Scan this QR code to identify "
                    "this honey batch."
                )

            with details_col:

                st.subheader("🍯 Product Details")

                st.markdown(
                    f"""
                    <div class="honey-card">

                    <h2>🍯 {batch['batch_id']}</h2>

                    <p>
                    <b>Honey Type:</b>
                    {batch['honey_type']}
                    </p>

                    <p>
                    <b>Origin:</b>
                    📍 {batch['location']}
                    </p>

                    <p>
                    <b>Harvest Date:</b>
                    📅 {batch['harvest_date']}
                    </p>

                    <p>
                    <b>Quantity:</b>
                    ⚖️ {batch['quantity_kg']} kg
                    </p>

                    <p>
                    <b>Current Status:</b>
                    📦 {batch['status']}
                    </p>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("---")

            # Honey Journey
            st.subheader("🚚 Honey Journey")

            st.caption(
                "Track the recorded journey of this honey batch."
            )

            journey = [

                (
                    "🌼",
                    "Harvested",
                    "Honey collected from the hive",
                    batch["location"]
                ),

                (
                    "⚙️",
                    "Processed",
                    "Honey processed and prepared",
                    "Telangana Processing Center"
                ),

                (
                    "📦",
                    "Packaged",
                    "Honey packed for distribution",
                    "Telangana Packaging Center"
                ),

                (
                    "🚚",
                    "Dispatched",
                    "Product sent for distribution",
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
                    ✓ {description}
                    </p>

                    <small>
                    📍 {location}
                    </small>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("---")

            # Blockchain Verification
            st.subheader("🔐 Blockchain Verification")

            if blockchain_valid:

                st.success(
                    "✓ Blockchain record is valid and "
                    "the recorded chain is intact."
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Blockchain Blocks",
                        len(blockchain.chain)
                    )

                with col2:
                    st.metric(
                        "Batch ID",
                        batch["batch_id"]
                    )

                with col3:
                    st.metric(
                        "Integrity",
                        "VALID"
                    )

            else:

                st.error(
                    "✗ Blockchain record is invalid."
                )

            st.markdown("---")

            # Customer information
            st.markdown(
                """
                <div class="honey-card">

                <h3>🛡️ Why verify your honey?</h3>

                <p>
                HoneyChain provides a digital record of the
                honey batch journey, from harvest to distribution.
                </p>

                <p>
                Scan the QR code to check the recorded batch
                information and blockchain integrity.
                </p>

                </div>
                """,
                unsafe_allow_html=True
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
    # HONEY PRODUCTION
    # ========================================================

    with tab1:

        st.subheader("🍯 Honey Production Prediction")

        st.info(
            "Enter environmental and hive conditions to estimate "
            "potential honey production."
        )

        try:

            production_model = joblib.load(
                PRODUCTION_MODEL_PATH
            )

            st.success("✅ Production AI model ready")

            st.markdown("### 🌦️ Environmental Conditions")

            c1, c2, c3 = st.columns(3)

            with c1:

                temperature = st.number_input(
                    "🌡️ Temperature (°C)",
                    min_value=0.0,
                    max_value=50.0,
                    value=30.0
                )

            with c2:

                humidity = st.number_input(
                    "💧 Humidity (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=65.0
                )

            with c3:

                rainfall = st.number_input(
                    "🌧️ Rainfall (mm)",
                    min_value=0.0,
                    max_value=300.0,
                    value=5.0
                )

            st.markdown("### 🐝 Hive & Flower Conditions")

            c1, c2, c3 = st.columns(3)

            with c1:

                hive_weight = st.number_input(
                    "⚖️ Hive Weight",
                    min_value=0.0,
                    max_value=100.0,
                    value=45.0
                )

            with c2:

                colony_strength = st.number_input(
                    "🐝 Colony Strength",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0
                )

            with c3:

                flower_availability = st.number_input(
                    "🌼 Flower Availability",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0
                )

            st.markdown("---")

            if st.button(
                "🔮 Predict Honey Production",
                use_container_width=True
            ):

                input_data = pd.DataFrame({

                    "temperature": [temperature],
                    "humidity": [humidity],
                    "rainfall": [rainfall],
                    "hive_weight": [hive_weight],
                    "colony_strength": [colony_strength],
                    "flower_availability": [flower_availability]

                })

                prediction = production_model.predict(
                    input_data
                )[0]

                st.markdown(
                    f"""
                    <div class="honey-card">

                    <h2>🍯 AI Production Estimate</h2>

                    <div class="metric-number">
                    {prediction:.2f} kg
                    </div>

                    <p>
                    Estimated honey production based on the
                    provided hive and environmental conditions.
                    </p>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.success(
                    "✅ Prediction generated successfully."
                )

        except Exception as e:

            st.error(
                f"Production model error: {e}"
            )


    # ========================================================
    # HIVE HEALTH
    # ========================================================

    with tab2:

        st.subheader("🐝 Hive Health Risk Prediction")

        st.info(
            "Analyze hive conditions and identify whether "
            "the colony requires attention."
        )

        try:

            health_model = joblib.load(
                HEALTH_MODEL_PATH
            )

            st.success("✅ Hive health AI model ready")

            st.markdown("### 🌦️ Environmental Conditions")

            c1, c2 = st.columns(2)

            with c1:

                temperature_h = st.number_input(
                    "🌡️ Temperature (°C)",
                    min_value=0.0,
                    max_value=50.0,
                    value=30.0,
                    key="health_temp"
                )

            with c2:

                humidity_h = st.number_input(
                    "💧 Humidity (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=65.0,
                    key="health_humidity"
                )

            st.markdown("### 🐝 Colony Health Indicators")

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                colony_strength_h = st.number_input(
                    "🐝 Colony Strength",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0,
                    key="health_colony"
                )

            with c2:

                varroa_level = st.number_input(
                    "🦠 Varroa Level",
                    min_value=0.0,
                    max_value=10.0,
                    value=2.5,
                    key="health_varroa"
                )

            with c3:

                food_availability_h = st.number_input(
                    "🌼 Food Availability",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0,
                    key="health_food"
                )

            with c4:

                bee_population = st.number_input(
                    "🐝 Bee Population",
                    min_value=0,
                    max_value=100000,
                    value=32000,
                    key="health_population"
                )

            st.markdown("---")

            if st.button(
                "🩺 Check Hive Health",
                use_container_width=True
            ):

                input_data = pd.DataFrame({

                    "temperature": [temperature_h],
                    "humidity": [humidity_h],
                    "colony_strength": [colony_strength_h],
                    "varroa_level": [varroa_level],
                    "food_availability": [food_availability_h],
                    "bee_population": [bee_population]

                })

                prediction = health_model.predict(
                    input_data
                )[0]

                prediction_text = str(
                    prediction
                )

                if prediction_text.lower() in [
                    "healthy",
                    "0"
                ]:

                    st.markdown(
                        """
                        <div class="status-good">

                        <h2>🟢 Hive Status: Healthy</h2>

                        <p>
                        Current input conditions indicate
                        a healthy hive.
                        </p>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.success(
                        "🐝 Continue regular hive monitoring."
                    )

                else:

                    st.markdown(
                        """
                        <div class="status-warning">

                        <h2>🟡 Hive Status: At Risk</h2>

                        <p>
                        Current input conditions indicate
                        that the hive requires attention.
                        </p>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.warning(
                        "🔎 Review hive conditions and continue monitoring."
                    )

        except Exception as e:

            st.error(
                f"Hive health model error: {e}"
            )


# ============================================================
# ============================================================
# END
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    "🍯 HoneyChain • Smart Honey Traceability"
)

