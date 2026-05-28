# app.py
# 필요한 패키지 설치:
# pip install streamlit google-api-python-client pandas matplotlib seaborn wordcloud konlpy

import re
from datetime import datetime

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from konlpy.tag import Okt
from googleapiclient.discovery import build

# -----------------------------
# Streamlit 기본 설정
# -----------------------------
st.set_page_config(
    page_title="YouTube 댓글 분석기",
    layout="wide"
)

st.title("📺 YouTube 댓글 데이터 분석 웹앱")
st.markdown("유튜브 영상 댓글을 수집하고 시각화하여 사용자 반응을 분석합니다.")

# -----------------------------
# 유튜브 API 키 입력
# -----------------------------
st.sidebar.header("🔑 YouTube API 설정")
api_key = st.sidebar.text_input(
    "YouTube Data API Key 입력",
    type="password"
)

# -----------------------------
# 영상 링크 입력
# -----------------------------
video_url = st.text_input(
    "유튜브 영상 링크 입력",
    placeholder="https://www.youtube.com/watch?v=xxxxxxxx"
)

# -----------------------------
# 댓글 수 슬라이더
# -----------------------------
comment_limit = st.slider(
    "수집할 댓글 수",
    min_value=20,
    max_value=10000,
    value=200,
    step=20
)

# -----------------------------
# 유튜브 video_id 추출 함수
# -----------------------------
def extract_video_id(url):
    patterns = [
        r"v=([a-zA-Z0-9_-]+)",
        r"youtu\.be/([a-zA-Z0-9_-]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None

# -----------------------------
# 댓글 수집 함수
# -----------------------------
def get_youtube_comments(api_key, video_id, max_comments):

    youtube = build("youtube", "v3", developerKey=api_key)

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request and len(comments) < max_comments:
        response = request.execute()

        for item in response["items"]:

            snippet = item["snippet"]["topLevelComment"]["snippet"]

            comment = snippet["textDisplay"]
            like_count = snippet["likeCount"]
            published_at = snippet["publishedAt"]

            comments.append({
                "comment": comment,
                "likes": like_count,
                "published_at": published_at
            })

            if len(comments) >= max_comments:
                break

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    return pd.DataFrame(comments)

# -----------------------------
# 워드클라우드 생성
# -----------------------------
def generate_wordcloud(text):

    okt = Okt()

    nouns = okt.nouns(text)

    # 2글자 이상 명사만 사용
    nouns = [word for word in nouns if len(word) > 1]

    text_data = " ".join(nouns)

    wordcloud = WordCloud(
        font_path="malgun.ttf",  # 윈도우 한글 폰트
        width=800,
        height=400,
        background_color="white"
    ).generate(text_data)

    return wordcloud

# -----------------------------
# 분석 시작 버튼
# -----------------------------
if st.button("댓글 분석 시작"):

    if not api_key:
        st.error("YouTube API Key를 입력해주세요.")
        st.stop()

    video_id = extract_video_id(video_url)

    if not video_id:
        st.error("올바른 유튜브 링크를 입력해주세요.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_youtube_comments(
            api_key,
            video_id,
            comment_limit
        )

    if df.empty:
        st.warning("댓글을 가져오지 못했습니다.")
        st.stop()

    st.success(f"{len(df)}개의 댓글 수집 완료!")

    # -----------------------------
    # 데이터 전처리
    # -----------------------------
    df["published_at"] = pd.to_datetime(df["published_at"])
    df["hour"] = df["published_at"].dt.hour

    # -----------------------------
    # 데이터 미리보기
    # -----------------------------
    st.subheader("📄 댓글 데이터")

    st.dataframe(df.head(20), use_container_width=True)

    # -----------------------------
    # 시간대별 댓글 추이
    # -----------------------------
    st.subheader("⏰ 시간대별 댓글 추이")

    hourly_counts = (
        df.groupby("hour")
        .size()
        .reset_index(name="count")
    )

    fig1, ax1 = plt.subplots(figsize=(10, 4))

    ax1.plot(
        hourly_counts["hour"],
        hourly_counts["count"],
        marker="o"
    )

    ax1.set_xlabel("시간")
    ax1.set_ylabel("댓글 수")
    ax1.set_title("시간대별 댓글 수")

    st.pyplot(fig1)

    # -----------------------------
    # 좋아요 수 분석
    # -----------------------------
    st.subheader("👍 댓글 좋아요 수 분석")

    fig2, ax2 = plt.subplots(figsize=(10, 4))

    ax2.hist(df["likes"], bins=30)

    ax2.set_xlabel("좋아요 수")
    ax2.set_ylabel("댓글 개수")
    ax2.set_title("댓글 좋아요 분포")

    st.pyplot(fig2)

    # 상위 좋아요 댓글
    st.subheader("🔥 좋아요 TOP 댓글")

    top_comments = df.sort_values(
        by="likes",
        ascending=False
    ).head(10)

    st.dataframe(
        top_comments[["comment", "likes"]],
        use_container_width=True
    )

    # -----------------------------
    # 워드클라우드
    # -----------------------------
    st.subheader("☁️ 자주 등장하는 단어")

    all_text = " ".join(df["comment"].astype(str))

    wordcloud = generate_wordcloud(all_text)

    fig3, ax3 = plt.subplots(figsize=(12, 6))

    ax3.imshow(wordcloud, interpolation="bilinear")
    ax3.axis("off")

    st.pyplot(fig3)

    # -----------------------------
    # 통계 요약
    # -----------------------------
    st.subheader("📊 댓글 통계 요약")

    col1, col2, col3 = st.columns(3)

    col1.metric("총 댓글 수", len(df))
    col2.metric("평균 좋아요 수", round(df["likes"].mean(), 2))
    col3.metric("최대 좋아요 수", int(df["likes"].max()))

    # CSV 다운로드
    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="youtube_comments.csv",
        mime="text/csv"
    )
