import streamlit as st
from src.collector import OfficialCollector


st.set_page_config(
    page_title='공문 분류기',
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    cs_body()

    return None


def cs_body():
    if not st.button('공문 분류 시작하기'):
        return

    collector = OfficialCollector()


if __name__ == '__main__':
    main()
