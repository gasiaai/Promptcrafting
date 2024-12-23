import streamlit as st
import openai
import configparser
import csv
import os

# -----------------------------
# กำหนด path สำหรับไฟล์ต่าง ๆ
# -----------------------------
# ในตัวอย่างนี้ จะถือว่าไฟล์ ini และ txt อยู่ในโฟลเดอร์เดียวกัน
# กับสคริปต์ Streamlit นี้
script_dir = os.path.dirname(os.path.abspath(__file__))

# -----------------------------
# ฟังก์ชันอ่าน/เขียน settings.ini
# -----------------------------
def read_settings():
    config = configparser.ConfigParser()
    settings_path = os.path.join(script_dir, 'settings.ini')
    if os.path.exists(settings_path):
        config.read(settings_path, encoding='utf-8')
        settings = config['DEFAULT']
        return {
            'api_key': settings.get('api_key', ''),
            'initial_keywords': settings.get('initial_keywords', ''),
            'temperature': settings.getfloat('temperature', 5.0),
            'num_prompts': settings.getint('num_prompts', 1),
            'selected_param': settings.get('selected_param', ''),
            'model': settings.get('model', 'gpt-4o-mini')
        }
    else:
        return {
            'api_key': '',
            'initial_keywords': '',
            'temperature': 5.0,
            'num_prompts': 1,
            'selected_param': '',
            'model': 'gpt-4o-mini'
        }

def save_settings(api_key, initial_keywords, temperature, num_prompts, selected_param, model):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'api_key': api_key,
        'initial_keywords': initial_keywords,
        'temperature': temperature,
        'num_prompts': num_prompts,
        'selected_param': selected_param,
        'model': model
    }
    settings_path = os.path.join(script_dir, 'settings.ini')
    with open(settings_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

# -----------------------------
# ฟังก์ชันอ่าน/เขียนไฟล์กฎ (rules.txt)
# -----------------------------
def read_rules():
    rules_path = os.path.join(script_dir, 'rules.txt')
    if os.path.exists(rules_path):
        with open(rules_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return ''

def create_default_rules():
    rules_path = os.path.join(script_dir, 'rules.txt')
    if not os.path.exists(rules_path):
        default_rules = (
            "your role is to generate concise names and detailed contexts for microstock images,"
            "No number list, ensuring each response fits within 77 tokens. It structures responses "
            "as numbered lists for more than two inputs, ensuring organization and clarity. Each entry "
            "is crafted without quotation marks \"\" or dashes -, using commas for separation. This "
            "approach focuses on straightforward, richly descriptive titles without vague language or "
            "mentioning camera specifics or photography techniques. For example, for suitable images, "
            "it might generate Watercolor Technique, Abstract vibrant background with watercolor "
            "blending, Artistic Expression, ensuring clarity, relevance, and rich descriptiveness "
            "within the token limit."
        )
        with open(rules_path, 'w', encoding='utf-8') as f:
            f.write(default_rules)

# -----------------------------
# ฟังก์ชันอ่าน/เขียนไฟล์พารามิเตอร์ (params.txt)
# -----------------------------
def read_params_options():
    params_path = os.path.join(script_dir, 'params.txt')
    if os.path.exists(params_path):
        with open(params_path, 'r', encoding='utf-8') as f:
            params_list = [line.strip() for line in f if line.strip()]
            return params_list
    else:
        return []

def create_default_params():
    params_path = os.path.join(script_dir, 'params.txt')
    if not os.path.exists(params_path):
        default_params = "--ar 16:9 --p\n--ar 21:9\n--ar 2:3"
        with open(params_path, 'w', encoding='utf-8') as f:
            f.write(default_params)

# เรียกใช้สร้างไฟล์เริ่มต้นหากไม่พบ
create_default_rules()
create_default_params()

# -----------------------------
# ส่วนหลักของแอป Streamlit
# -----------------------------
def main():
    st.title("Prompt Generator (Streamlit Version)")

    # โหลดการตั้งค่าเก่า (ถ้ามี)
    settings = read_settings()

    # -----------------------------
    # Sidebar สำหรับตั้งค่า
    # -----------------------------
    st.sidebar.header("Settings")
    api_key = st.sidebar.text_input("OpenAI API Key", value=settings['api_key'], type="password")
    model_name = st.sidebar.text_input("Model Name", value=settings['model'])
    initial_keywords = st.sidebar.text_input("Initial Keywords", value=settings['initial_keywords'])
    num_prompts = st.sidebar.number_input("Number of Prompts", min_value=1, max_value=100, value=settings['num_prompts'])
    temperature_slider = st.sidebar.slider("Temperature (0-10)", min_value=0, max_value=10, value=int(settings['temperature']))
    
    # อ่านรายการพารามิเตอร์จากไฟล์
    param_options = read_params_options()
    selected_param = st.sidebar.selectbox("Select Parameter", param_options, 
                                          index=param_options.index(settings['selected_param']) if settings['selected_param'] in param_options else 0 
                                          if len(param_options) > 0 else -1)
    
    # ปุ่มบันทึกการตั้งค่า
    if st.sidebar.button("Save Settings"):
        save_settings(api_key, initial_keywords, temperature_slider, num_prompts, selected_param, model_name)
        st.sidebar.success("Settings saved successfully.")

    # -----------------------------
    # ส่วนแสดงผลหลัก
    # -----------------------------
    st.write("## Generate Prompts")

    # ปุ่มสั่ง Generate
    if st.button("Generate Prompts"):
        if not api_key:
            st.error("Please enter your OpenAI API key.")
        elif not initial_keywords:
            st.error("Please enter initial keywords.")
        else:
            openai.api_key = api_key

            # อ่านกฎจาก rules.txt
            rules_content = read_rules()
            if not rules_content:
                st.error("Please make sure rules.txt exists and is not empty.")
            else:
                # เตรียม prompt
                system_message = "You are an AI assistant that generates concise prompts based on given keywords and rules."
                temperature_value = temperature_slider
                temperature_mapped = (temperature_value / 10) * 2  # 0-10 -> 0-2

                generated_prompts = []
                try:
                    for _ in range(num_prompts):
                        user_message = (
                            f"{rules_content}\n"
                            f"Initial keywords: {initial_keywords}\n"
                            "Generate a concise with good SEO title from the input, within 77 tokens.\n"
                            "Avoid photography-related words like realistic, natural lighting, photography, etc.\n"
                            "No quotation marks or dashes, use commas for separation if needed.\n"
                            "Focus on straightforward, richly descriptive titles without vague language or mentioning camera specifics or photography techniques.\n"
                            "Ensure the response is a single line."
                        )

                        response = openai.ChatCompletion.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_message}
                            ],
                            temperature=temperature_mapped,
                            max_tokens=77,
                            n=1,
                            stop=None
                        )

                        generated_text = response.choices[0].message['content'].strip()
                        # เพิ่มพารามิเตอร์ท้าย prompt
                        if selected_param:
                            generated_text += ' ' + selected_param
                        generated_prompts.append(generated_text)

                    # แสดงผล
                    st.success("Prompts generated successfully!")
                    for i, prompt in enumerate(generated_prompts, start=1):
                        st.text_area(f"Prompt #{i}", value=prompt, height=60)

                    # เก็บ prompts ไว้ใน session_state เพื่อใช้ต่อ (เช่น save CSV)
                    st.session_state['generated_prompts'] = generated_prompts

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    # -----------------------------
    # ปุ่มคัดลอกและบันทึก CSV
    # -----------------------------
    if 'generated_prompts' in st.session_state and st.session_state['generated_prompts']:
        prompts_text = "\n".join(st.session_state['generated_prompts'])
        
        # ปุ่มดาวน์โหลดเป็น CSV
        csv_file_name = "generated_prompts.csv"
        if st.download_button(
            label="Download Prompts as CSV",
            data=convert_to_csv(st.session_state['generated_prompts']),
            file_name=csv_file_name,
            mime="text/csv"
        ):
            st.success("CSV file is ready for download!")

        # ปุ่มคัดลอก (ให้ผู้ใช้ copy เองผ่าน text area)
        st.write("### Copy Prompts")
        st.text_area("All Prompts", value=prompts_text, height=150)

def convert_to_csv(prompts_list):
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Prompt'])
    for prompt in prompts_list:
        writer.writerow([prompt])
    return output.getvalue().encode('utf-8')

if __name__ == "__main__":
    main()
