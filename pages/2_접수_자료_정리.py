import streamlit as st
import json
import pandas as pd


def load_data(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_data(filepath, data):
    """JSON 파일에 데이터 저장"""
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def tasks_to_dataframe(tasks):
    """task를 DataFrame 형식으로 변환"""
    df_data = []
    for task in tasks:
        df_data.append({"공문명": task})
    return pd.DataFrame(df_data)


def dataframe_to_tasks(df):
    """DataFrame을 task 리스트로 변환"""
    tasks = []
    for _, row in df.iterrows():
        task = row['공문명']

        tasks.append(task)

    return tasks


# 앱 제목
st.title('🪧 할일 분류')

data_json_file = './data/docu_data.json'

# 데이터 로드
tasks = load_data(data_json_file)

# 과제카드 목록 생성
managers = list(tasks.keys())
selected_manager = st.selectbox('과제카드 선택', managers)

if selected_manager:
    # 선택된 담당자의 업무를 DataFrame으로 변환
    manager_tasks = tasks[selected_manager]
    df = tasks_to_dataframe(manager_tasks)

    # data_editor를 사용하여 업무 표시 및 편집
    edited_df = st.data_editor(
        df, num_rows="dynamic", width=600)

    # 변경사항 저장
    if st.button('변경사항 저장'):
        new_tasks = dataframe_to_tasks(edited_df)
        tasks[selected_manager] = new_tasks
        save_data(data_json_file, tasks)
        st.success('변경사항이 저장되었습니다.')

st.subheader('과제카드 관리')
# 담당자 삭제
if st.button('선택한 과제카드 삭제', type="primary") and selected_manager:
    del tasks[selected_manager]
    save_data(tasks)
    st.success(f'{selected_manager} 과제카드가 삭제되었습니다.')
    st.experimental_rerun()


# 새 담당자 추가
new_manager = st.text_input('새 과제카드 이름')
if st.button('새 과제카드 추가', type="secondary") and new_manager:
    if new_manager not in tasks:
        tasks[new_manager] = {[]}
        save_data(tasks)
        st.success(f'{new_manager} 과제카드가 추가되었습니다.')
        st.experimental_rerun()
    else:
        st.error('이미 존재하는 과제카드입니다.')
