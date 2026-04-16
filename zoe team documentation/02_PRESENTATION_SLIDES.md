# GlucoSense — Presentation Content (Slides 1–8)

**Project title:** GLUCOSENSE: A Decision Support System for Optimized Insulin Dose Recommendation and Personalized Nutritional Management.

Use this file as **slide copy** plus **speaker notes**. Each slide uses **On slide** (what the audience reads) and **Speaker notes** (what you say). **Slide 8** points to Mermaid diagrams in `03_UI_ARCHITECTURE_MERMAID.md`. Body text is written in **paragraphs**, not bullet lists.

---

## SLIDE 1 — Title

**Title**  
GLUCOSENSE: A Decision Support System for Optimized Insulin Dose Recommendation and Personalized Nutritional Management.

**Subtitle (optional)**  
Clinical decision support and nutrition workflows for Type 1 diabetes–oriented care (education / demonstration context).

**Project team (Zoe Team — update names if your roster differs)**  
Abaho Joy · Mucunguzi Godfrey · Wangolo Bachawa

**Affiliation**  
Uganda Christian University (UCU) — Faculty of Engineering, Design, and Technology / Computing and Technology  

**Date / course**  
*[Add presentation date and module code as required]*

---

## SLIDE 2 — Introduction and Background

**On slide (title):** Why this project matters

**On slide (text)**  
Diabetes is a **major global burden**, and **good control** reduces complications; **[IDF Atlas 11th ed., 2025](https://diabetesatlas.org/)** and **[WHO — Diabetes](https://www.who.int/health-topics/diabetes)** frame that burden at population level. **Algorithm-supported insulin** is gaining evidence (**e.g. [Nature Communications, 2025](https://www.nature.com/articles/s41467-025-63671-0)**), while reviews also insist that **AI** stay **transparent and safe** (**[Springer Die Diabetologie, 2025](https://link.springer.com/article/10.1007/s11428-025-01332-y)**). **Nutrition** must fit the **person** and **context** (**[Frontiers in Endocrinology, 2025](https://www.frontiersin.org/journals/endocrinology/articles/10.3389/fendo.2025.1690486/full)**).

**GlucoSense** is **web-based decision support**: **ML-assisted insulin guidance** together with a **nutrition application** (meal planning, search, chatbot, glucose logging).

**Speaker notes**  
Lead with **scale** and **why integrated care** matters. **Decision-support algorithms** for insulin appear next to demands for **explainability** and **real-life nutrition**. **GlucoSense** is introduced as **support** for the care team, not a stand-in for it.

**References (Slide 2)**  
Citations on this slide draw on the International Diabetes Federation *Diabetes Atlas* (11th ed., 2025) and global factsheet PDF, the World Health Organization diabetes topic page, Biester et al. (*Nature Communications*, 2025), Schumm-Draeger and Schmitt (*Die Diabetologie*, 2025), and Frontiers in Endocrinology (2025); URLs are listed in the **Consolidated reference list** at the end of this file.

---

## SLIDE 3 — Problem statement

**On slide (title):** The gap addressed

**On slide (text)**  
Where **specialists are scarce**, aligning **insulin** with **everyday eating** is difficult: **glucose**, **carbohydrate intake**, and **trust in software** all vary. Many tools are **opaque**, treat **food and insulin separately**, or fit **poorly** with **local diet** and **primary care**.

The need is **one coherent story**: **explainable dosing** and **personalized meals**, suited to **teaching** and **resource-limited** settings. **GlucoSense** combines **insulin support** and **embedded nutrition** (search, meal suggestions, chatbot, logs) in **one portal**. **Live hardware IoT** lies **outside** this project (see Scope).

**Speaker notes**  
Name the **pain**: **fragmented** tools and **black-box** AI. Stress that **patients and clinicians** need **insulin reasoning** and **meal guidance** **together**. Point forward to **Scope** for **limits** (no live **CGM** in this build).

---

## SLIDE 4 — Objectives

**On slide (title):** Project objectives

**On slide (text)**  
The project delivers **machine-learning-based insulin suggestions** from **structured assessments**, with **validation**, **records**, and **clinician dashboards** for **trends**, **alerts**, and **reports**. It also delivers a **nutrition layer**: **food search**, **meal recommendations**, **glucose logging**, and a conversational **assistant** for questions.

Nutrition is **embedded in the same portal** as the clinical workspace, with **single sign-on**, so **dosing** and **meal planning** form **one flow**. **Explainability** is used where the stack allows—surfacing **why** a dose is suggested. The work is **documented** together with its **boundary conditions**, including **no live IoT or CGM hardware** in this version, so the outcome remains a **reproducible academic artifact**.

**Speaker notes**  
Cover **clinical intelligence**, **nutrition**, **integration**, **explainability**, and **documented limits** in **under one minute**.

---

## SLIDE 5 — Scope

**On slide (title):** In scope vs. out of scope

**On slide (text)**  
**In scope**, the experience runs from **assessment** to **insulin suggestion**, then **alerts and checks**, and where the model allows, a **view of what influenced** the suggestion. **Care and nutrition share one portal**: the **clinical workspace** includes **embedded nutrition** (meal ideas, food search, coaching) under **one sign-in**. Users **search foods**, receive **meal recommendations**, **log glucose**, and use an **assistant**. The intended **setting** is **demonstration, teaching, and research**, not a **nationwide deployment**.

**Out of scope**, the build does **not** connect to **live CGM, pump, or wearable** streams; **illustrative charts** use **sample files** only. It does **not** claim **randomized-trial outcomes**, **HbA1c effects**, or **medical-device certification**. It does **not** provide a **complete** national or **fully culture-complete** food catalogue—only **starter** data that **can** grow. **Full hospital EHR** integration is also **excluded**.

**Speaker notes**  
If the slide is split visually (**in** vs **out**), walk each block once. Stress **decision-support prototype** for **learning**, not a **regulated commercial device** or **hardware platform**.

---

## SLIDE 6 — Literature review

**On slide (title):** Evidence base and consultation

**On slide (text)**  
Type 1 diabetes depends on **daily self-care**: **glucose patterns**, **insulin**, and **carbohydrates**. International guidance links **steady control** to lower risk of **acute** and **long-term** complications (**[WHO](https://www.who.int/health-topics/diabetes)**; **[ADA Type 1 self-care](https://diabetes.org/living-with-diabetes/type-1/type-1-self-care-manual)**). **Background review** of self-management literature **confirmed** that **continuous attention** and **support** matter.

A **nutritionist** was **consulted** on **food choice**, **meal timing**, and **carb planning** in the **same control loop** as **insulin**; **that input** **informed** pairing **insulin decision support** with **meal-oriented** features in **GlucoSense**.

A **structured literature review** was **conducted** on clinical decision support for type 1 diabetes: **major databases** were searched through 2025, **records** were screened and filtered against **defined criteria**, and **eligible** work was synthesized for **recurring themes**. **Published systems** often combine machine-learning prediction with rule-based safety; **explainability** is widely discussed; **meal-related** features recur—yet **few** integrated, easy-to-audit tools span insulin and nutrition for front-line care in one workflow.

The **GlucoSense** design **combined** **clinical guidance**, **nutritionist** input, **desk research**, and **synthesis** from the review—toward **transparent**, **meal-aware** support alongside **insulin** reasoning.

---

## SLIDE 7 — Research methodology adopted (and why)

**On slide (title):** Research methodology and build

**On slide (text)**  
The **systematic literature review** was conducted under **PRISMA**. **Scopus** and **Web of Science** were searched (2017–2025) with keywords on type 1 diabetes, clinical decision support, machine learning, rules, explainable AI, and meal or nutrition planning. Studies were included when they described integrated CDS combining learning with rules, and explainability or nutrition, with clinical or implementation relevance. Non-English work, papers without implementable substance, and irrelevant type-2-only designs were excluded. A reproducible map of evidence was produced.

Design-science research applied identified gaps to software: requirements were derived from the review; architecture linked insulin and meals with embedded access and shared authentication; models, recommendation engines, and interfaces were implemented; evaluation emphasized traceable outputs and documented limits. The literature review summarizes what the field emphasizes; the design cycle yielded one working artifact with configurable food data, chat, and constraints.

**Speaker notes**  
About two minutes: PRISMA structured the search; design science moved from evidence to implementation.

---

## SLIDE 8 — Design(s)

**On slide (title):** Architecture at a glance

**On slide (text)**  
**Color-coded Mermaid diagrams** in [`03_UI_ARCHITECTURE_MERMAID.md`](./03_UI_ARCHITECTURE_MERMAID.md) summarize **system topology**, the **recommendation** path, **chatbot** routing, and the **UI** layout. Figures can be **exported** to **PNG** or **SVG** for the slide deck.

**Speaker notes**  
Walk through **one** figure—usually **topology** showing the **clinical** stack, **meal** stack, and **embed**. Say clearly that **insulin** and **nutrition** meet in **one browser** journey.

---

## Consolidated reference list (copy to final slide or appendix)

**External web (Slides 2–3).** Background on **burden** and **care** draws on the **[World Health Organization](https://www.who.int/health-topics/diabetes)** diabetes topic page, the **[International Diabetes Federation](https://diabetesatlas.org/)** *Diabetes Atlas* (11th edition, 2025), and the **[IDF global factsheet PDF](https://diabetesatlas.org/media/uploads/sites/3/2025/04/IDF_Atlas_11th_Edition_2025_Global-Factsheet.pdf)** (2025). Further support for **algorithm-guided insulin** and **nutrition in automated delivery** comes from **[Nature Communications](https://www.nature.com/articles/s41467-025-63671-0)** (2025, Bayesian decision support in MDI), **[Springer *Die Diabetologie*](https://link.springer.com/article/10.1007/s11428-025-01332-y)** (2025, AI and insulin therapy), and **[Frontiers in Endocrinology](https://www.frontiersin.org/journals/endocrinology/articles/10.3389/fendo.2025.1690486/full)** (2025).

**Literature review — clinical context (Slide 6).** [WHO — Diabetes](https://www.who.int/health-topics/diabetes); [American Diabetes Association — Type 1 Diabetes Self-Care Manual](https://diabetes.org/living-with-diabetes/type-1/type-1-self-care-manual) (nutrition, glucose targets, and complications-oriented self-management).

**Team systematic review (Slides 6–7).** Abaho J., Mucunguzi G., Wangolo B., *Explainable AI–Driven Clinical Decision Support and Personalized Meal Planning for Type 1 Diabetes: A PRISMA-Guided Systematic Literature Review* (2025); local file **`Systematic_Literature_Review.pdf`**.

**Repository technical documentation.** Monorepo structure and pipelines are described in **`ARCHITECTURE.md`** and **`SYSTEM_PIPELINE.md`** at the GlucoSense project root.

