import streamlit as st
import openai
import configparser
import csv
import os

# -----------------------------
# กำหนด path สำหรับไฟล์ settings.ini และ rules.txt
# -----------------------------
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
            'model': settings.get('model', 'gpt-4o-mini'),
            'ar_mode': settings.get('ar_mode', 'Preset'),       # เก็บโหมดว่า "Preset" หรือ "Custom"
            'ar_preset': settings.get('ar_preset', '--ar 16:9'), # เก็บค่าที่เลือกในกรณีเป็น Preset
            'ar_custom': settings.get('ar_custom', '')          # เก็บค่าที่ผู้ใช้กรอกเอง
        }
    else:
        return {
            'api_key': '',
            'initial_keywords': '',
            'temperature': 5.0,
            'num_prompts': 1,
            'model': 'gpt-4o-mini',
            'ar_mode': 'Preset',
            'ar_preset': '--ar 16:9',
            'ar_custom': ''
        }

def save_settings(api_key, initial_keywords, temperature, num_prompts, model, ar_mode, ar_preset, ar_custom):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'api_key': api_key,
        'initial_keywords': initial_keywords,
        'temperature': temperature,
        'num_prompts': num_prompts,
        'model': model,
        'ar_mode': ar_mode,
        'ar_preset': ar_preset,
        'ar_custom': ar_custom
    }
    settings_path = os.path.join(script_dir, 'settings.ini')
    with open(settings_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

# -----------------------------
# ฟังก์ชันอ่าน rules.txt
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
            "generate concise names and detailed contexts for microstock images, ensuring each response fits within 77 tokens. It structures responses as numbered lists for more than two inputs, ensuring organization and clarity. Each entry is crafted without quotation marks or dashes, using commas for separation. This approach focuses on straightforward, richly descriptive titles without vague language or mentioning camera specifics or photography techniques. For example, for suitable images, it might generate 1. Watercolor Technique, Abstract vibrant background with watercolor blending, Artistic Expression, ensuring clarity, relevance, and rich descriptiveness within the token limit. "
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

create_default_rules()  # ถ้าไม่มีไฟล์ rules.txt จะสร้างไฟล์ default ให้

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

    st.sidebar.markdown("---")
    st.sidebar.write("**Aspect Ratio Setting**")
    ar_mode = st.sidebar.radio("Choose AR Mode", options=["Preset", "Custom"], index=0 if settings['ar_mode'] == "Preset" else 1)

    # ถ้าเลือก preset
    preset_choices = ["--ar 3:2", "--ar 16:9", "--ar 7:3", "--ar 1:1"]
    if ar_mode == "Preset":
        if settings['ar_preset'] in preset_choices:
            default_index = preset_choices.index(settings['ar_preset'])
        else:
            default_index = 1  # default: --ar 16:9

        ar_preset = st.sidebar.selectbox("Select a preset AR", preset_choices, index=default_index)
        ar_custom = ""
    else:
        # เลือก Custom => ให้กรอกค่าเอง
        ar_preset = ""
        ar_custom = st.sidebar.text_input("Enter custom AR (e.g. --ar 5:4)", value=settings['ar_custom'])

    # ปุ่มบันทึกการตั้งค่า
    if st.sidebar.button("Save Settings"):
        save_settings(api_key, initial_keywords, temperature_slider, num_prompts, model_name, ar_mode, ar_preset, ar_custom)
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
                # เลือกว่าจะใช้ preset หรือ custom
                final_ar = ar_preset if ar_mode == "Preset" else ar_custom

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
                        # ถ้า final_ar มีค่า (ไม่เป็นค่าว่าง) ให้เพิ่มต่อท้าย
                        if final_ar:
                            generated_text += " " + final_ar

                        generated_prompts.append(generated_text)

                    # แสดงผล
                    st.success("Prompts generated successfully!")
                    for i, prompt in enumerate(generated_prompts, start=1):
                        st.text_area(f"Prompt #{i}", value=prompt, height=100)

                    # เก็บ prompts ไว้ใน session_state เพื่อใช้ต่อ (เช่น save CSV)
                    st.session_state['generated_prompts'] = generated_prompts

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    # -----------------------------
    # ปุ่มบันทึก CSV และ Copy
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

        # แสดง TextArea สำหรับคัดลอกทั้งหมดทีเดียว
        st.write("### Copy All Prompts")
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
