import streamlit as st
import requests
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = "https://ebrvulnhjojujhqgpzpi.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVicnZ1bG5oam9qdWpocWdwenBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MjEyMzAsImV4cCI6MjA2MDE5NzIzMH0.5FiBy0egJ_bBrpfIuKhjGlXAL1WpiCdPo43wf-O0LZw"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# API headers
headers = {
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "conversation_step" not in st.session_state:
    st.session_state.conversation_step = "start"
if "farm_data" not in st.session_state:
    st.session_state.farm_data = {}
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# Call Supabase Edge Function
def call_conversation_api(user_id, action, data=None):
    payload = {"user_id": user_id, "action": action}
    if data:
        payload["data"] = data
    response = requests.post(
        f"{SUPABASE_URL}/functions/v1/conversation",
        headers=headers,
        json=payload
    )
    if response.status_code != 200:
        error_msg = response.json().get('error', 'Unknown error')
        raise Exception(f"API Error: {error_msg}")
    return response.json()

# Login
def login():
    st.subheader("Đăng nhập")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Mật khẩu", type="password", key="login_password")
    if st.button("Đăng nhập"):
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = response.user
            st.session_state.conversation_step = "start"
            st.session_state.farm_data = {}
            st.session_state.error_message = None
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi đăng nhập: {str(e)}")

# Signup
def signup():
    st.subheader("Đăng ký")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Mật khẩu", type="password", key="signup_password")
    if st.button("Đăng ký"):
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            st.session_state.user = response.user
            if response.user:
                st.success("Đăng ký thành công! Vui lòng đăng nhập.")
            else:
                st.info("Vui lòng kiểm tra email để xác nhận tài khoản.")
        except Exception as e:
            st.error(f"Lỗi đăng ký: {str(e)}")

# Logout
def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.conversation_step = "start"
    st.session_state.farm_data = {}
    st.session_state.error_message = None
    st.session_state.last_result = None
    st.success("Đăng xuất thành công!")
    st.rerun()

# Conversation
def conversation():
    if not st.session_state.user:
        st.warning("Vui lòng đăng nhập để tiếp tục!")
        return

    user_id = st.session_state.user.id

    if st.session_state.error_message:
        st.error(st.session_state.error_message)

    if st.session_state.conversation_step == "start":
        try:
            response = call_conversation_api(user_id, "start")
            st.session_state.conversation_step = response["message"]
        except Exception as e:
            st.session_state.error_message = f"Lỗi: {str(e)}"
            st.rerun()

    # Hiển thị kết quả nếu đã hoàn thành
    if st.session_state.conversation_step == "done":
        st.success(f"**Kết quả Dự đoán Năng suất**: {st.session_state.last_result}")
        if st.button("Bắt đầu lại"):
            st.session_state.conversation_step = "ask_photo"
            st.session_state.last_result = None
            st.session_state.error_message = None
            st.rerun()
        return

    st.write(f"**Bot**: {st.session_state.conversation_step}")

    if "size of your farm" in st.session_state.conversation_step.lower():
        size = st.number_input("Kích thước nông trại (hectares)", min_value=0.1, step=0.1)
        if st.button("Gửi kích thước"):
            try:
                st.session_state.farm_data["size_hectares"] = size
                response = call_conversation_api(user_id, "submit_size", {"size_hectares": size})
                st.session_state.conversation_step = response["message"]
                st.session_state.error_message = None
                st.rerun()
            except Exception as e:
                st.session_state.error_message = f"Lỗi: {str(e)}"
                st.rerun()

    elif "coffee trees do you have" in st.session_state.conversation_step.lower():
        tree_count = st.number_input("Số lượng cây cà phê", min_value=1, step=1)
        if st.button("Gửi số cây"):
            try:
                st.session_state.farm_data["tree_count"] = tree_count
                response = call_conversation_api(user_id, "submit_trees", {"tree_count": tree_count})
                st.session_state.conversation_step = response["message"]
                st.session_state.error_message = None
                st.rerun()
            except Exception as e:
                st.session_state.error_message = f"Lỗi: {str(e)}"
                st.rerun()

    elif "where is your farm located" in st.session_state.conversation_step.lower():
        location = st.text_input("Vị trí nông trại (ví dụ: Da Lat, Vietnam)")
        if st.button("Gửi vị trí"):
            try:
                data = {
                    "location": location,
                    "size_hectares": st.session_state.farm_data["size_hectares"],
                    "tree_count": st.session_state.farm_data["tree_count"]
                }
                response = call_conversation_api(user_id, "submit_location", data)
                st.session_state.farm_data["location"] = location
                st.session_state.conversation_step = response["message"]
                st.session_state.error_message = None
                st.rerun()
            except Exception as e:
                st.session_state.error_message = f"Lỗi: {str(e)}"
                st.rerun()

    elif "upload a photo" in st.session_state.conversation_step.lower() or st.session_state.conversation_step == "ask_photo":
        image_url = st.text_input("URL ảnh cây cà phê (ví dụ: https://example.com/photo.jpg)")
        if st.button("Gửi ảnh"):
            try:
                response = call_conversation_api(user_id, "submit_photo", {
                    "image_url": image_url,
                    "size_hectares": st.session_state.farm_data.get("size_hectares"),
                    "tree_count": st.session_state.farm_data.get("tree_count"),
                    "location": st.session_state.farm_data.get("location")
                })
                st.session_state.last_result = response["message"]
                st.session_state.conversation_step = "done"
                st.session_state.error_message = None
                st.rerun()
            except Exception as e:
                st.session_state.error_message = f"Lỗi: {str(e)}"
                st.rerun()

# Main page
def main():
    st.title("Ứng dụng Dự đoán Năng suất Cà phê")

    if not st.session_state.user:
        tab1, tab2 = st.tabs(["Đăng nhập", "Đăng ký"])
        with tab1:
            login()
        with tab2:
            signup()
    else:
        st.write(f"Chào **{st.session_state.user.email}**!")
        if st.button("Đăng xuất"):
            logout()
        conversation()

if __name__ == "__main__":
    main()
