
import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="반려묘 추천기 (필터/간식 1회량)", page_icon="🐱", layout="centered")
st.title("🐱 반려묘 사료·간식 추천기 (필터 + 간식 1회 급여량)")

st.caption("학습용 예제입니다. 실제 급여 전에는 반드시 성분표/급여지침과 수의사 상담을 참고하세요.")

# -------------------- 데이터 로드 --------------------
@st.cache_data
def load_catalog(path: str):
    df = pd.read_csv(path)
    for col in ["ingredients", "tags", "brand"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    num_cols = ["moisture_pct", "kcal_per_100g", "magnesium_mg_per_100kcal", "phosphorus_pct_dm", "sodium_pct_dm", "treat_kcal_per_piece"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

CATALOG = load_catalog("catalog.csv")

# -------------------- 알러지 동의어 --------------------
ALLERGY_SYNONYMS = {
    "닭": ["닭", "치킨", "계육", "chicken"],
    "소": ["소", "소고기", "비프", "beef"],
    "어류": ["어류", "생선", "연어", "참치", "고등어", "fish", "salmon", "tuna", "mackerel"],
    "칠면조": ["칠면조", "터키", "turkey"],
    "양": ["양", "램", "양고기", "lamb"],
    "오리": ["오리", "duck"],
    "계란": ["계란", "달걀", "egg"],
    "유제품": ["우유", "유청", "치즈", "유당", "milk", "lactose", "whey"],
    "곡물": ["밀", "보리", "옥수수", "글루텐", "밀글루텐", "wheat", "corn", "gluten"]
}

def expand_allergy_terms(allergy_list):
    expanded = set()
    for a in allergy_list:
        key = a.strip().lower()
        if not key:
            continue
        expanded.add(key)
        for k, syns in ALLERGY_SYNONYMS.items():
            syns_lower = [s.lower() for s in syns]
            if key in syns_lower or key == k.lower():
                expanded.update(syns_lower)
    return expanded

# -------------------- 유지보수 함수 --------------------
def life_stage(age):
    return "키튼" if age < 1 else ("어덜트" if age < 10 else "시니어")

def estimate_daily_calories(weight, activity, neutered, stage):
    rer = 70 * (weight ** 0.75)
    factor = 1.0
    if neutered == "예":
        factor -= 0.05
    if activity == "낮음":
        factor -= 0.1
    elif activity == "높음":
        factor += 0.15
    if stage == "키튼":
        factor += 0.25
    elif stage == "시니어":
        factor -= 0.05
    return max(120, int(round(rer * factor)))

def grams_per_day(daily_kcal, kcal_per_100g):
    if pd.isna(kcal_per_100g) or kcal_per_100g <= 0:
        return None
    return int(round(daily_kcal / kcal_per_100g * 100))

# -------------------- STEP 1: 폼 --------------------
if "stage" not in st.session_state:
    st.session_state.stage = "form"
if "inputs" not in st.session_state:
    st.session_state.inputs = {}

if st.session_state.stage == "form":
    with st.form("cat_form"):
        st.subheader("기본 정보")
        col1, col2, col3 = st.columns(3)
        with col1:
            weight = st.number_input("몸무게(kg)", 0.5, 15.0, 4.0, 0.1)
        with col2:
            age_years = st.number_input("나이(년)", 0.0, 25.0, 3.0, 0.5)
        with col3:
            neutered = st.selectbox("중성화", ["예", "아니오"], index=0)

        activity = st.selectbox("활동량", ["낮음", "보통", "높음"], index=1)

        st.subheader("병력/건강")
        conditions = st.multiselect(
            "해당 항목 선택",
            ["비만 경향", "FLUTD/요로기계", "신장 질환(CKD)", "간 질환", "소화 민감성/IBD", "헤어볼", "치아 문제"]
        )

        st.subheader("기호성/선호")
        col4, col5 = st.columns(2)
        with col4:
            texture = st.selectbox("형태 선호", ["드라이", "습식/파우치", "동일"], index=2)
        with col5:
            flavor = st.selectbox("단백질 선호", ["닭", "어류", "소", "칠면조/기타", "상관없음"], index=4)

        st.subheader("알러지")
        base_allergy = st.multiselect("자주 있는 알러지", list(ALLERGY_SYNONYMS.keys()))
        custom_allergy = st.text_input("기타 알러지(쉼표로 구분, 예: 연어, 치즈, 밀글루텐)")

        st.subheader("가격/브랜드 필터")
        brand_list = sorted([b for b in CATALOG["brand"].dropna().unique() if b])
        brand_filter = st.multiselect("브랜드(복수 선택 가능, 선택 안 하면 전체)", brand_list, default=[])
        price_filter = st.multiselect("가격대(복수 선택 가능)", ["저가","중간","프리미엄"], default=["저가","중간","프리미엄"])

        submitted = st.form_submit_button("✅ 확인 후 추천 보기")
        if submitted:
            st.session_state.inputs = {
                "weight": weight,
                "age_years": age_years,
                "neutered": neutered,
                "activity": activity,
                "conditions": conditions,
                "texture": texture,
                "flavor": flavor,
                "base_allergy": base_allergy,
                "custom_allergy": custom_allergy,
                "brand_filter": brand_filter,
                "price_filter": price_filter,
            }
            st.session_state.stage = "result"
            st.rerun()

# -------------------- STEP 2: 결과 --------------------
if st.session_state.stage == "result":
    inp = st.session_state.inputs

    st.subheader("입력 요약")
    c1, c2, c3 = st.columns(3)
    stage = life_stage(inp["age_years"])
    daily_kcal = estimate_daily_calories(inp["weight"], inp["activity"], inp["neutered"], stage)
    with c1:
        st.markdown(f"**체중**: {inp['weight']} kg")
        st.markdown(f"**나이/단계**: {inp['age_years']}년 / {stage}")
    with c2:
        st.markdown(f"**중성화**: {inp['neutered']}")
        st.markdown(f"**활동량**: {inp['activity']}")
    with c3:
        st.markdown("**건강상태**")
        st.caption(", ".join(inp["conditions"]) if inp["conditions"] else "없음/미선택")

    custom_allergy_tokens = [t.strip() for t in inp["custom_allergy"].split(",") if t.strip()]
    allergy_terms = set([a.lower() for a in inp["base_allergy"]]) | set([t.lower() for t in custom_allergy_tokens])
    expanded_allergies = expand_allergy_terms(allergy_terms)

    st.info(f"**권장 1일 필요 열량(학습용 추정)**: 약 **{daily_kcal} kcal/일** · 간식은 보통 **10% 이하(≈ {int(daily_kcal*0.1)} kcal)** 권장")

    # 점수 규칙 상수
    FLUTD_MAGNESIUM_MAX = 25
    CKD_PHOSPHORUS_MAX = 0.6
    CKD_SODIUM_MAX = 0.4

    # 필터링(브랜드/가격대)
    filtered = CATALOG.copy()
    if inp["brand_filter"]:
        filtered = filtered[filtered["brand"].isin(inp["brand_filter"])]
    if inp["price_filter"]:
        filtered = filtered[filtered["price_tier"].isin(inp["price_filter"])]

    def score_row(row):
        score = 0
        reasons = []
        tags = set(str(row.tags).split(";")) if pd.notna(row.tags) else set()

        # 기호성/가격
        if str(row.price_tier) in inp["price_filter"]:
            score += 1; reasons.append(f"{row.price_tier} 가격")
        if str(row.texture) == inp["texture"] and inp["texture"] != "동일":
            score += 1; reasons.append(f"{inp['texture']} 선호")
        if inp["flavor"] != "상관없음" and str(row.protein) == inp["flavor"]:
            score += 1; reasons.append(f"{inp['flavor']} 선호")

        # 단계
        if stage == "키튼" and "키튼" in tags:
            score += 2; reasons.append("키튼용")
        if stage == "시니어" and "시니어" in tags:
            score += 2; reasons.append("시니어용")

        # 체중/열량
        if "비만 경향" in inp["conditions"] and pd.notna(row.kcal_per_100g) and row.kcal_per_100g <= 330:
            score += 2; reasons.append("저칼로리")
        if inp["activity"] == "높음" and pd.notna(row.kcal_per_100g) and row.kcal_per_100g >= 360:
            score += 1; reasons.append("활동량 높음에 적합")

        # 요로/수분/마그네슘
        if "FLUTD/요로기계" in inp["conditions"]:
            if str(row.texture).startswith("습식") or (pd.notna(row.moisture_pct) and row.moisture_pct >= 70):
                score += 3; reasons.append("요로 건강(높은 수분)")
            if pd.notna(row.magnesium_mg_per_100kcal) and row.magnesium_mg_per_100kcal <= FLUTD_MAGNESIUM_MAX:
                score += 2; reasons.append("마그네슘 낮음")

        # CKD
        if "신장 질환(CKD)" in inp["conditions"]:
            if pd.notna(row.phosphorus_pct_dm) and row.phosphorus_pct_dm <= CKD_PHOSPHORUS_MAX:
                score += 2; reasons.append("낮은 인")
            if pd.notna(row.sodium_pct_dm) and row.sodium_pct_dm <= CKD_SODIUM_MAX:
                score += 1; reasons.append("나트륨 적당")

        # 소화/헤어볼/치아
        if "소화 민감성/IBD" in inp["conditions"] and "소화 민감성" in tags:
            score += 2; reasons.append("소화에 순함")
        if "헤어볼" in inp["conditions"] and "헤어볼" in tags:
            score += 2; reasons.append("헤어볼 관리")
        if "치아 문제" in inp["conditions"] and ("치아 관리" in tags or "덴탈" in str(row.name)):
            score += 2; reasons.append("치아 관리")

        # 알러지 회피
        blob = " ".join([str(row.name), str(row.protein), str(row.ingredients)]).lower()
        if any(term in blob for term in expanded_allergies):
            score -= 6; reasons.append("알러지 의심 성분 회피 필요")

        return score, reasons

    scored = []
    for _, r in filtered.iterrows():
        sc, rs = score_row(r)
        rec = r.to_dict()
        rec["score"] = sc
        rec["reasons"] = rs
        if rec["type"] == "사료" and pd.notna(rec.get("kcal_per_100g")):
            rec["recommended_grams_per_day"] = int(round(daily_kcal / rec["kcal_per_100g"] * 100))
        else:
            rec["recommended_grams_per_day"] = None
        # Treat serving: pieces per day based on 10% kcal budget
        if rec["type"] == "간식" and pd.notna(rec.get("treat_kcal_per_piece")) and rec["treat_kcal_per_piece"] > 0:
            budget = int(daily_kcal * 0.1)
            rec["treat_pieces_per_day"] = max(1, budget // int(rec["treat_kcal_per_piece"]))
        else:
            rec["treat_pieces_per_day"] = None
        scored.append(rec)

    tab_food, tab_treat = st.tabs(["🍽 사료 추천", "🍘 간식 추천"])

    def render_list(items, is_treat=False):
        if not items:
            st.warning("후보가 없습니다. 필터를 조정해 보세요.")
            return
        top_n = st.slider("표시 개수", 1, len(items), min(3, len(items)), key=("slider_treat" if is_treat else "slider_food"))
        for item in sorted(items, key=lambda x: x["score"], reverse=True)[:top_n]:
            with st.container(border=True):
                st.markdown(f"### {item['name']} · *{item['type']}*")
                cols = st.columns(3)
                cols[0].metric("예상 점수", item["score"])
                cols[1].write(f"브랜드: **{item.get('brand','')}** · 형태: **{item['texture']}** · 단백질: **{item['protein']}**")
                cols[2].write(f"열량: **{item.get('kcal_per_100g', float('nan'))} kcal/100g** · 가격대: **{item['price_tier']}**")
                if not is_treat and item.get("recommended_grams_per_day"):
                    st.success(f"권장 1일 급여량(사료): **약 {item['recommended_grams_per_day']} g/일**")
                if is_treat:
                    budget = int(daily_kcal * 0.1)
                    if item.get("treat_pieces_per_day"):
                        st.info(f"간식 권장 한도(10%): **≈ {budget} kcal/일** · 1개당 {int(item.get('treat_kcal_per_piece'))} kcal → **하루 {item['treat_pieces_per_day']}개**")
                    else:
                        st.info(f"간식 권장 한도(10%): **≈ {budget} kcal/일** · (CSV에 1개당 kcal를 넣으면 개수 계산 가능)")
                if item["reasons"]:
                    st.caption("추천 이유: " + ", ".join(item["reasons"]))

    with tab_food:
        render_list([x for x in scored if x["type"] == "사료"], is_treat=False)

    with tab_treat:
        render_list([x for x in scored if x["type"] == "간식"], is_treat=True)

    with st.expander("전체 표 보기"):
        show_cols = ["brand","name","type","texture","protein","kcal_per_100g","moisture_pct","price_tier","tags","magnesium_mg_per_100kcal","phosphorus_pct_dm","sodium_pct_dm","treat_kcal_per_piece","score","recommended_grams_per_day","treat_pieces_per_day"]
        st.dataframe(pd.DataFrame(scored)[show_cols], use_container_width=True)

    col1, col2 = st.columns(2)
    if col1.button("🔁 다시 입력하기"):
        st.session_state.stage = "form"
        st.rerun()
    if col2.button("❌ 종료"):
        st.success("브라우저 탭을 닫거나 터미널에서 Ctrl+C 로 종료할 수 있습니다.")
