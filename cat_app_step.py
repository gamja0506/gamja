
import streamlit as st

st.set_page_config(page_title="반려묘 사료/간식 추천기", page_icon="🐱", layout="centered")

# -------------------- 상태 초기화 --------------------
if "stage" not in st.session_state:
    st.session_state.stage = "form"  # "form" -> "result"
if "inputs" not in st.session_state:
    st.session_state.inputs = {}

st.title("🐱 반려묘 사료·간식 추천기")

st.caption("학습용 예제이며, 수의사 상담을 대체하지 않습니다. 제품 급여 전 성분표/급여지침을 꼭 확인하세요.")

# -------------------- 예시 카탈로그 --------------------
# 간단 키워드 검색을 위해 name/protein/ingredients를 준비
CATALOG = [
    {
        "name": "유리너리 케어 어류 파우치",
        "type": "사료",
        "texture": "습식/파우치",
        "protein": "어류",
        "ingredients": ["참치", "연어", "타우린"],
        "moisture_pct": 78,
        "kcal_per_100g": 90,
        "price_tier": "프리미엄",
        "tags": ["요로기계", "높은 수분"]
    },
    {
        "name": "키드니 케어 칠면조 드라이",
        "type": "사료",
        "texture": "드라이",
        "protein": "칠면조/기타",
        "ingredients": ["칠면조", "쌀", "감자"],
        "moisture_pct": 10,
        "kcal_per_100g": 360,
        "price_tier": "프리미엄",
        "tags": ["신장 케어", "중단백"]
    },
    {
        "name": "어덜트 라이트 닭 드라이",
        "type": "사료",
        "texture": "드라이",
        "protein": "닭",
        "ingredients": ["치킨", "현미"],
        "moisture_pct": 10,
        "kcal_per_100g": 330,
        "price_tier": "중간",
        "tags": ["체중 관리"]
    },
    {
        "name": "키튼 고단백 닭 드라이",
        "type": "사료",
        "texture": "드라이",
        "protein": "닭",
        "ingredients": ["치킨", "완두"],
        "moisture_pct": 10,
        "kcal_per_100g": 400,
        "price_tier": "저가",
        "tags": ["키튼", "성장"]
    },
    {
        "name": "시니어 헤어볼 어류 드라이",
        "type": "사료",
        "texture": "드라이",
        "protein": "어류",
        "ingredients": ["연어", "보리"],
        "moisture_pct": 10,
        "kcal_per_100g": 320,
        "price_tier": "중간",
        "tags": ["시니어", "헤어볼"]
    },
    {
        "name": "센시티브 터키 파우치",
        "type": "사료",
        "texture": "습식/파우치",
        "protein": "칠면조/기타",
        "ingredients": ["칠면조", "호박"],
        "moisture_pct": 80,
        "kcal_per_100g": 85,
        "price_tier": "프리미엄",
        "tags": ["소화 민감성"]
    },
    {
        "name": "덴탈 바이트(간식)",
        "type": "간식",
        "texture": "드라이",
        "protein": "닭",
        "ingredients": ["치킨", "셀룰로오스"],
        "moisture_pct": 10,
        "kcal_per_100g": 300,
        "price_tier": "중간",
        "tags": ["치아 관리"]
    },
    {
        "name": "저칼로리 트릿 어류(간식)",
        "type": "간식",
        "texture": "습식/파우치",
        "protein": "어류",
        "ingredients": ["참치", "연어"],
        "moisture_pct": 75,
        "kcal_per_100g": 120,
        "price_tier": "프리미엄",
        "tags": ["체중 관리"]
    }
]

# 알러지 키워드 동의어(간단 버전)
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

# -------------------- STEP 1: 입력 폼 --------------------
if st.session_state.stage == "form":
    st.subheader("1) 반려묘 기본 정보 입력")

    with st.form("cat_form"):
        name = st.text_input("이름(선택)", value=st.session_state.inputs.get("name", ""))
        col1, col2, col3 = st.columns(3)
        with col1:
            weight = st.number_input("몸무게(kg)", 0.5, 15.0, st.session_state.inputs.get("weight", 4.0), 0.1)
        with col2:
            age_years = st.number_input("나이(년)", 0.0, 25.0, st.session_state.inputs.get("age_years", 3.0), 0.5)
        with col3:
            neutered = st.selectbox("중성화", ["예", "아니오"], index=0 if st.session_state.inputs.get("neutered", "예")=="예" else 1)

        activity = st.selectbox("활동량", ["낮음", "보통", "높음"], index=["낮음","보통","높음"].index(st.session_state.inputs.get("activity","보통")))

        st.subheader("2) 병력/건강 상태")
        conditions = st.multiselect(
            "해당 항목 선택(복수)",
            ["비만 경향", "FLUTD/요로기계", "신장 질환(CKD)", "간 질환", "소화 민감성/IBD", "헤어볼", "치아 문제"],
            default=st.session_state.inputs.get("conditions", [])
        )

        st.subheader("3) 기호성/선호")
        col4, col5 = st.columns(2)
        with col4:
            texture = st.selectbox("형태 선호", ["드라이", "습식/파우치", "동일"], index=["드라이","습식/파우치","동일"].index(st.session_state.inputs.get("texture","동일")))
        with col5:
            flavor = st.selectbox("단백질 선호", ["닭", "어류", "소", "칠면조/기타", "상관없음"], index=["닭","어류","소","칠면조/기타","상관없음"].index(st.session_state.inputs.get("flavor","상관없음")))

        st.subheader("4) 알러지 입력")
        base_allergy = st.multiselect(
            "자주 있는 알러지(선택)",
            ["닭", "소", "어류", "칠면조", "양", "오리", "계란", "유제품", "곡물"],
            default=st.session_state.inputs.get("base_allergy", [])
        )
        custom_allergy = st.text_input(
            "기타 알러지(쉼표로 구분, 예: 연어, 치즈, 밀글루텐)",
            value=st.session_state.inputs.get("custom_allergy", "")
        )

        st.subheader("5) 가격대")
        price_tier = st.select_slider("선호 가격대", options=["저가","중간","프리미엄"], value=st.session_state.inputs.get("price_tier","중간"))

        submitted = st.form_submit_button("✅ 확인 후 추천 보기")
        if submitted:
            st.session_state.inputs = {
                "name": name,
                "weight": weight,
                "age_years": age_years,
                "neutered": neutered,
                "activity": activity,
                "conditions": conditions,
                "texture": texture,
                "flavor": flavor,
                "base_allergy": base_allergy,
                "custom_allergy": custom_allergy,
                "price_tier": price_tier,
            }
            st.session_state.stage = "result"
            st.rerun()

# -------------------- STEP 2: 추천 결과 --------------------
if st.session_state.stage == "result":
    inp = st.session_state.inputs
    st.subheader("입력 확인")
    with st.expander("입력한 정보 열기/닫기", expanded=True):
        st.write(inp)

    # --- 알러지 세트 정리
    custom_allergy_tokens = [t.strip() for t in inp["custom_allergy"].split(",") if t.strip()]
    allergy_terms = set([a.lower() for a in inp["base_allergy"]]) | set([t.lower() for t in custom_allergy_tokens])
    allergy_terms = expand_allergy_terms(allergy_terms)

    def life_stage(age):
        return "키튼" if age < 1 else ("어덜트" if age < 10 else "시니어")

    def score_item(item):
        score = 0
        reasons = []

        stage = life_stage(inp["age_years"])
        if stage == "키튼" and "키튼" in item["tags"]:
            score += 2; reasons.append("키튼용")
        if stage == "시니어" and "시니어" in item["tags"]:
            score += 2; reasons.append("시니어용")

        # 요로/수분
        if "FLUTD/요로기계" in inp["conditions"]:
            if item["texture"].startswith("습식") or item.get("moisture_pct", 0) >= 70:
                score += 3; reasons.append("요로 건강에 도움(높은 수분)")
            if "요로기계" in item["tags"]:
                score += 2; reasons.append("유리너리 케어")

        # 신장
        if "신장 질환(CKD)" in inp["conditions"] and "신장 케어" in item["tags"]:
            score += 3; reasons.append("신장 케어")

        # 체중/열량
        if "비만 경향" in inp["conditions"] and item["kcal_per_100g"] <= 330:
            score += 2; reasons.append("저칼로리")
        if inp["activity"] == "높음" and item["kcal_per_100g"] >= 360:
            score += 1; reasons.append("활동량 높음에 적합")

        # 소화/헤어볼/치아
        if "소화 민감성/IBD" in inp["conditions"] and "소화 민감성" in item["tags"]:
            score += 2; reasons.append("소화에 순함")
        if "헤어볼" in inp["conditions"] and "헤어볼" in item["tags"]:
            score += 2; reasons.append("헤어볼 관리")
        if "치아 문제" in inp["conditions"] and ("덴탈" in item["name"] or "치아" in " ".join(item["tags"])):
            score += 2; reasons.append("치아 관리")

        # 알러지 회피: name/protein/ingredients 전체에서 키워드 검색
        text_blob = " ".join([item["name"], item["protein"], " ".join(item.get("ingredients", []))]).lower()
        if any(term in text_blob for term in allergy_terms):
            score -= 6; reasons.append("알러지 의심 성분 회피 필요")

        # 기호성/가격대
        if inp["texture"] != "동일" and item["texture"] == inp["texture"]:
            score += 1; reasons.append(f"{inp['texture']} 선호")
        if inp["flavor"] != "상관없음" and item["protein"] == inp["flavor"]:
            score += 1; reasons.append(f"{inp['flavor']} 선호")
        if item["price_tier"] == inp["price_tier"]:
            score += 1; reasons.append(f"{inp['price_tier']} 가격")

        return score, reasons

    # --- 추천 계산
    results = []
    for it in CATALOG:
        sc, rs = score_item(it)
        results.append({**it, "score": sc, "reasons": rs})
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    pet_label = f"**{inp['name']}**에게" if inp['name'] else "반려묘에게"
    st.subheader(f"{pet_label} 맞춤 추천")

    top_n = st.slider("표시 개수", 1, len(CATALOG), 3)
    for item in results[:top_n]:
        with st.container(border=True):
            st.markdown(f"### {item['name']}  ·  *{item['type']}*")
            cols = st.columns(3)
            cols[0].metric("예상 점수", item["score"])
            cols[1].write(f"형태: **{item['texture']}** · 단백질: **{item['protein']}**")
            cols[2].write(f"수분: **{item.get('moisture_pct','?')}%** · 열량: **{item['kcal_per_100g']} kcal/100g** · 가격대: **{item['price_tier']}**")
            if item["reasons"]:
                st.caption("추천 이유: " + ", ".join(item["reasons"]))

    with st.expander("전체 후보(간단 표)"):
        table = [{k:v for k,v in r.items() if k not in ["reasons"]} for r in results]
        st.dataframe(table, use_container_width=True)

    col_a, col_b = st.columns(2)
    if col_a.button("🔁 다시 입력하기"):
        st.session_state.stage = "form"
        st.rerun()
    if col_b.button("❌ 종료"):
        st.success("앱을 종료하려면 브라우저 탭을 닫거나, 터미널에서 Ctrl+C 를 누르세요.")
