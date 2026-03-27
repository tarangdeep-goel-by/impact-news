# laterals_2 Weight Re-Rating — Gemini 3.1 Pro

<details><summary>Thinking (3173 chars)</summary>

**Edge Calibration Deep Dive**

Okay, here's the deal: I'm in charge of meticulously calibrating this causal knowledge graph, and I need to get the edge properties – the weight, polarity, and delay – precisely right for each event related to Indian citizens' lives. No room for error. My goal is a YAML array, nothing more, nothing less, and *no* markdown fences or commentary. This is pure data.

The constraints are pretty clear. Weights have specific ranges tied to semantic meanings: "Near 1:1," "Strong but buffered," "Noticeable but diluted," "Weak, indirect," or "Remove." Polarity is either +1 (direct) or -1 (inverse). The time delays must be one of IMMEDIATE, SHORT_TERM, MEDIUM_TERM, or LONG_TERM.

Now, let's step through this, as I process it.

*   `hypertension` -> `heart_disease`: Weight of 0.85 – strong, but with a delay, so it's not instantaneous. Polarity +1, obviously a direct relationship. Delay is LONG\_TERM; it takes years.
*   `diabetes` -> `heart_disease`: 0.80, same logic. It's a risk factor, with management, but still, a LONG\_TERM delay.
*   `diabetes` -> `vision_care`: 0.75, a specific complication. The relationship is direct; LONG\_TERM delay.
*   `anxiety_disorders` -> `depression`: 0.70. Comorbidity is high, so MEDIUM\_TERM.
*   `depression` -> `substance_abuse`: 0.65 – noticeable, but not guaranteed. Medium term delay.
*   `childhood_malnutrition` -> `tuberculosis`: 0.75 - strong impact, Medium term.
*   `doctor_consultation` -> `blood_tests`: 0.85 – Very common. IMMEDIATE.
*   `doctor_consultation` -> `medical_imaging`: 0.65. IMMEDIATE.
*   `doctor_consultation` -> `generic_medicines`: 0.85. IMMEDIATE.
*   `diabetes` -> `home_monitoring_devices`: 0.90 – Standard of care. IMMEDIATE.
*   `hypertension` -> `home_monitoring_devices`: 0.75. IMMEDIATE.
*   `heart_disease` -> `surgical_procedures`: 0.70 – Major outcome; SHORT\_TERM.
*   `cancer` -> `surgical_procedures`: 0.80. Primary treatment; SHORT\_TERM.
*   `cancer` -> `medical_imaging`: 0.90. Immediate diagnosis and monitoring.
*   `asthma` -> `chronic_disease_medication`: 0.90 – Standard. IMMEDIATE.
*   `copd` -> `hospital_beds`: 0.75. SHORT\_TERM.
*   `dengue` -> `blood_tests`: 0.95. IMMEDIATE.
*   `dengue` -> `hospital_beds`: 0.70. IMMEDIATE.
*   `influenza_and_viral_fever` -> `painkillers_and_antipyretics`: 0.90. IMMEDIATE.
*   `tuberculosis` -> `antibiotics`: 0.95. IMMEDIATE.
*   `cholera_and_diarrhea` -> `hospital_beds`: 0.65. Immediate.
*   `anxiety_disorders` -> `therapy_consultation`: 0.60, but there's access issues and stigma. SHORT\_TERM.
*   `depression` -> `psychiatric_medication`: 0.70. SHORT\_TERM.
*   `maternity_services` -> `pediatric_vaccines`: 0.95. IMMEDIATE.
*   `maternity_services` -> `nutritional_supplements`: 0.90. IMMEDIATE.
*   `ayurvedic_medicines` -> `generic_medicines`: 0.40 – Substitution effect: -1 Polarity. Immediate.
*   `homeopathic_medicines` -> `generic_medicines`: 0.30, weak substitution; -1 Polarity. Immediate.
*   `generic_medicines` -> `chronic_disease_medication`: 0.85. Immediate.
*   `retail_sugar` -> `obesity`: 0.60 – diet is complex. LONG\_TERM.
*   `polluted_surface_water` -> `typhoid`: 0.80. SHORT\_

</details>

## Response

```yaml
- from: hypertension
  to: heart_disease
  weight: 0.85
  polarity: 1
  delay: LONG_TERM
  reasoning: Chronic high blood pressure is a leading, direct cause of cardiovascular diseases over years of exposure.
- from: diabetes
  to: heart_disease
  weight: 0.80
  polarity: 1
  delay: LONG_TERM
  reasoning: Prolonged high blood sugar significantly increases heart disease risk over years, though manageable with medication.
- from: diabetes
  to: vision_care
  weight: 0.75
  polarity: 1
  delay: LONG_TERM
  reasoning: Diabetic retinopathy develops over years, directly necessitating specialized vision care.
- from: anxiety_disorders
  to: depression
  weight: 0.70
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Chronic anxiety frequently exhausts mental resources, leading to depressive episodes over weeks to months.
- from: depression
  to: substance_abuse
  weight: 0.65
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Depression often drives individuals to self-medicate with substances over weeks to months.
- from: childhood_malnutrition
  to: tuberculosis
  weight: 0.75
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Malnutrition severely weakens the immune system, making children highly susceptible to TB infections over months.
- from: doctor_consultation
  to: blood_tests
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Physician visits directly and immediately generate referrals for diagnostic blood work.
- from: doctor_consultation
  to: medical_imaging
  weight: 0.65
  polarity: 1
  delay: IMMEDIATE
  reasoning: Clinical evaluations frequently result in immediate orders for X-rays or ultrasounds.
- from: doctor_consultation
  to: generic_medicines
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Consultations almost always result in immediate prescriptions for generic medicines.
- from: diabetes
  to: home_monitoring_devices
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: A diabetes diagnosis creates an immediate, near-universal need for home glucometers.
- from: hypertension
  to: home_monitoring_devices
  weight: 0.75
  polarity: 1
  delay: IMMEDIATE
  reasoning: Managing hypertension often requires patients to immediately purchase home blood pressure monitors.
- from: heart_disease
  to: surgical_procedures
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: Advanced cardiovascular conditions frequently necessitate bypasses or stents within days to weeks of diagnosis.
- from: cancer
  to: surgical_procedures
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: Oncology treatments heavily rely on surgical procedures to remove tumors shortly after diagnosis.
- from: cancer
  to: medical_imaging
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Cancer diagnosis and monitoring require immediate and continuous PET/CT scan imaging.
- from: asthma
  to: chronic_disease_medication
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Asthma directly and immediately requires the ongoing use of inhalers and chronic medications.
- from: copd
  to: hospital_beds
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: Acute exacerbations of COPD frequently lead to emergency inpatient hospital admissions.
- from: dengue
  to: blood_tests
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Dengue fever requires immediate, continuous blood tests to monitor dangerous drops in platelet counts.
- from: dengue
  to: hospital_beds
  weight: 0.70
  polarity: 1
  delay: IMMEDIATE
  reasoning: Severe dengue hemorrhagic fever directly forces patients into inpatient hospital beds for fluid management.
- from: influenza_and_viral_fever
  to: painkillers_and_antipyretics
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Viral fevers immediately drive the consumption of over-the-counter antipyretics like paracetamol.
- from: tuberculosis
  to: antibiotics
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Tuberculosis infections directly and immediately require long-term, multi-drug antibiotic regimens.
- from: cholera_and_diarrhea
  to: hospital_beds
  weight: 0.65
  polarity: 1
  delay: IMMEDIATE
  reasoning: Severe dehydration from cholera directly necessitates emergency hospital admission for IV fluids.
- from: anxiety_disorders
  to: therapy_consultation
  weight: 0.60
  polarity: 1
  delay: SHORT_TERM
  reasoning: Diagnosed anxiety disorders drive patients to seek therapy, though access and stigma dilute the pass-through.
- from: depression
  to: psychiatric_medication
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: Clinical depression frequently results in the prescription of psychiatric medications like antidepressants.
- from: maternity_services
  to: pediatric_vaccines
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Maternity ward deliveries directly initiate the mandatory protocol of newborn pediatric vaccinations.
- from: maternity_services
  to: nutritional_supplements
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Antenatal maternity care universally prescribes iron, calcium, and folic acid supplements to pregnant women.
- from: ayurvedic_medicines
  to: generic_medicines
  weight: 0.40
  polarity: -1
  delay: IMMEDIATE
  reasoning: Increased use of Ayurvedic treatments moderately reduces the consumption of allopathic generic medicines for primary care.
- from: homeopathic_medicines
  to: generic_medicines
  weight: 0.30
  polarity: -1
  delay: IMMEDIATE
  reasoning: Homeopathic remedies serve as a minor alternative, weakly competing with conventional generic medicines.
- from: generic_medicines
  to: chronic_disease_medication
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Generic drug manufacturers supply the vast majority of affordable daily medications for chronic diseases in India.
- from: retail_sugar
  to: obesity
  weight: 0.60
  polarity: 1
  delay: LONG_TERM
  reasoning: High consumption of retail sugar contributes significantly to caloric surplus and rising obesity rates over years.
- from: polluted_surface_water
  to: typhoid
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: Contaminated local water bodies directly transmit Salmonella typhi, causing typhoid outbreaks in days to weeks.
- from: stagnant_water_pools
  to: chikungunya
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: Urban stagnant water pools breed vector mosquitoes, directly leading to chikungunya infections within weeks.
- from: winter_smog
  to: asthma
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Severe winter smog directly and immediately triggers acute asthma attacks and respiratory inflammation.
- from: winter_smog
  to: copd
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: High levels of toxic winter smog immediately worsen COPD, causing severe breathing crises.
- from: outdoor_heat
  to: hospital_beds
  weight: 0.70
  polarity: 1
  delay: IMMEDIATE
  reasoning: Extreme outdoor heatwaves cause heatstroke and severe dehydration, filling emergency hospital beds.
- from: road_traffic_accidents
  to: surgical_procedures
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Severe road traffic accidents directly and immediately necessitate emergency orthopedic and trauma surgeries.
- from: road_traffic_accidents
  to: hospital_beds
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Victims of road traffic accidents directly require immediate inpatient hospital beds for recovery.
- from: startup_layoffs
  to: depression
  weight: 0.60
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Sudden job losses trigger financial panic and can lead to clinical depression among affected workers over weeks.
- from: domestic_violence
  to: depression
  weight: 0.85
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Victims of ongoing domestic violence directly suffer from severe psychological trauma and depression.
- from: child_abuse_and_pocso
  to: therapy_consultation
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: Survivors of child abuse require specialized psychological therapy to process trauma, often initiated shortly after reporting.
- from: maternity_services
  to: maternity_leave_benefits
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Utilization of maternity services directly triggers the activation of statutory maternity leave benefits for formal workers.
- from: surgical_procedures
  to: health_insurance_premium
  weight: 0.75
  polarity: 1
  delay: LONG_TERM
  reasoning: High volumes of expensive surgical claims force insurers to raise general health insurance premiums annually.
- from: childhood_malnutrition
  to: school_examinations
  weight: 0.70
  polarity: -1
  delay: LONG_TERM
  reasoning: Chronic childhood malnutrition impairs cognitive development, reducing student performance in school examinations over years.
- from: influenza_and_viral_fever
  to: school_examinations
  weight: 0.60
  polarity: -1
  delay: IMMEDIATE
  reasoning: Outbreaks of viral fever cause student absenteeism, negatively impacting participation in immediate school examinations.
- from: anganwadi_system
  to: government_schools
  weight: 0.85
  polarity: 1
  delay: LONG_TERM
  reasoning: Anganwadis provide early childhood care that directly feeds students into primary government schools.
- from: private_preschools
  to: private_schools
  weight: 0.90
  polarity: 1
  delay: LONG_TERM
  reasoning: Private preschools prepare and funnel children directly into formal private schooling systems.
- from: mid_day_meal
  to: government_schools
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Guaranteed daily meals strongly incentivize attendance and enrollment in government schools.
- from: free_textbooks_uniforms
  to: government_schools
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: Free educational supplies reduce out-of-pocket costs, boosting government school retention.
- from: private_schools
  to: school_fees
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Enrollment in private institutions directly generates immediate and recurring school fee obligations.
- from: government_schools
  to: state_board_exams
  weight: 0.90
  polarity: 1
  delay: LONG_TERM
  reasoning: Government school students predominantly appear for state board examinations at the end of secondary education.
- from: private_schools
  to: cbse_exams
  weight: 0.80
  polarity: 1
  delay: LONG_TERM
  reasoning: A majority of private schools are affiliated with and prepare students for central CBSE exams.
- from: cbse_exams
  to: engineering_entrance
  weight: 0.75
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Clearing senior secondary board exams is a strict prerequisite for appearing in engineering entrance tests.
- from: cbse_exams
  to: medical_entrance
  weight: 0.75
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Board exam completion is mandatory before students can sit for medical entrance exams like NEET.
- from: state_board_exams
  to: university_entrance
  weight: 0.80
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: State board graduates form the primary applicant pool for general university entrance exams like CUET.
- from: engineering_entrance
  to: engineering_education
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Successful clearance of entrance exams directly allocates seats in undergraduate engineering colleges.
- from: medical_entrance
  to: medical_education
  weight: 0.95
  polarity: 1
  delay: SHORT_TERM
  reasoning: Medical entrance scores are the sole gateway to securing admission in medical colleges in India.
- from: management_entrance
  to: management_education
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Exams like CAT directly supply qualified candidates to postgraduate management programs.
- from: university_entrance
  to: arts_science_commerce
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: University entrance exams filter students into general undergraduate degree programs.
- from: engineering_entrance
  to: offline_coaching_centers
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: High competition for engineering seats creates massive immediate demand for specialized offline coaching institutes.
- from: medical_entrance
  to: offline_coaching_centers
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: The hyper-competitive nature of medical exams drives students to enroll in dedicated coaching hubs like Kota.
- from: civil_services_exam
  to: offline_coaching_centers
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: UPSC preparation heavily relies on structured guidance from offline coaching institutes in major hubs.
- from: offline_coaching_centers
  to: coaching_fees
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Enrollment in physical test prep centers directly incurs substantial and immediate coaching fees.
- from: private_tutors
  to: coaching_fees
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Hiring personal tutors for supplemental education adds directly to household coaching expenses.
- from: test_prep_edtech
  to: offline_coaching_centers
  weight: 0.65
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: Online test prep platforms offer cheaper alternatives that draw students away from physical coaching centers.
- from: k12_edtech
  to: private_tutors
  weight: 0.60
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: App-based learning and doubt-solving platforms reduce the reliance on traditional private home tutors.
- from: educational_scholarships
  to: college_university_fees
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: Scholarships directly offset and reduce the net tuition fees payable by university students.
- from: engineering_education
  to: college_university_fees
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Pursuing technical degrees involves high, immediate tuition and laboratory fees.
- from: medical_education
  to: college_university_fees
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Medical degrees, especially in private colleges, generate exorbitant tuition fee burdens.
- from: arts_science_commerce
  to: banking_ssc_exams
  weight: 0.80
  polarity: 1
  delay: LONG_TERM
  reasoning: General degree graduates form the bulk of applicants for banking and staff selection exams.
- from: arts_science_commerce
  to: civil_services_exam
  weight: 0.75
  polarity: 1
  delay: LONG_TERM
  reasoning: Graduates from arts and sciences frequently pursue careers in civil services.
- from: broadband_network_quality
  to: k12_edtech
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Seamless streaming of online K-12 classes requires stable and high-speed home broadband.
- from: smartphone_device
  to: k12_edtech
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Access to mobile-first educational applications necessitates smartphone ownership.
- from: laptop_computer
  to: higher_ed_online_degrees
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Completing online university coursework and proctored exams strictly requires a personal computer.
- from: government_teacher_jobs
  to: government_schools
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: State-appointed teachers provide the essential instructional labor required to run government schools.
- from: tur_dal
  to: mid_day_meal
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Pulses are a mandatory protein component supplied to school kitchens for mid-day meals.
- from: medical_education
  to: doctor_consultation
  weight: 0.90
  polarity: 1
  delay: LONG_TERM
  reasoning: Medical colleges train and supply the certified physicians who provide healthcare consultations.
- from: management_education
  to: private_bank_jobs
  weight: 0.80
  polarity: 1
  delay: LONG_TERM
  reasoning: MBA programs funnel graduates directly into corporate roles within private sector banks.
- from: technical_vocational_training
  to: factory_worker_jobs
  weight: 0.85
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: ITIs and vocational institutes train skilled blue-collar workers directly for manufacturing roles.
- from: banking_ssc_exams
  to: psu_bank_jobs
  weight: 0.95
  polarity: 1
  delay: SHORT_TERM
  reasoning: IBPS and SBI exams directly recruit candidates for probationary officer and clerical roles in public banks.
- from: offline_coaching_centers
  to: pg_and_hostel_fees
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: The migration of students to coaching hubs directly drives immediate demand for local PG accommodations.
- from: mid_day_meal
  to: childhood_malnutrition
  weight: 0.80
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: Consistent provision of nutritious school meals directly reduces the incidence of stunting and wasting in children over months.
- from: arts_science_commerce
  to: urban_unemployment_rate
  weight: 0.70
  polarity: 1
  delay: LONG_TERM
  reasoning: A surplus of general degree graduates lacking specialized skills contributes significantly to educated urban unemployment.
- from: corporate_upskilling
  to: it_sector_salary
  weight: 0.75
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Acquiring new certifications and tech skills directly enables IT professionals to negotiate higher wages.
- from: engineering_entrance
  to: anxiety_disorders
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: The extreme pressure to clear JEE creates severe psychological stress and anxiety among adolescents.
- from: medical_entrance
  to: anxiety_disorders
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: The hyper-competitive NEET environment directly triggers mental health crises in medical aspirants.
- from: language_soft_skills
  to: private_bank_jobs
  weight: 0.65
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: English proficiency and communication training improve employability for customer-facing banking roles.
- from: riots_and_clashes
  to: curfews_and_section_144
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Violent civil unrest directly and immediately triggers authorities to impose curfews to restore public order.
- from: riots_and_clashes
  to: assault_and_battery
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Mob violence during riots inherently involves physical assaults and battery against individuals.
- from: riots_and_clashes
  to: fire_hazards
  weight: 0.75
  polarity: 1
  delay: IMMEDIATE
  reasoning: Arson and vandalism during violent clashes create immediate urban fire hazards.
- from: fire_hazards
  to: structural_collapse
  weight: 0.60
  polarity: 1
  delay: SHORT_TERM
  reasoning: Severe fires weaken building foundations and load-bearing walls, leading to structural collapse.
- from: structural_collapse
  to: stampedes
  weight: 0.50
  polarity: 1
  delay: IMMEDIATE
  reasoning: The sudden collapse of infrastructure in crowded areas triggers mass panic and subsequent stampedes.
- from: burglary_and_theft
  to: fir_registration
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Victims of property crimes must register an FIR to initiate police investigations and claim insurance.
- from: vehicle_theft
  to: fir_registration
  weight: 0.95
  polarity: 1
  delay: SHORT_TERM
  reasoning: Stolen vehicles require an immediate FIR registration for tracking and motor insurance claims.
- from: assault_and_battery
  to: fir_registration
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: Victims of violent physical attacks file FIRs to pursue criminal charges, though some cases go unreported.
- from: sexual_assault
  to: fir_registration
  weight: 0.50
  polarity: 1
  delay: SHORT_TERM
  reasoning: Survivors of sexual violence register FIRs, though severe social stigma often suppresses or delays reporting.
- from: domestic_violence
  to: fir_registration
  weight: 0.45
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Prolonged domestic abuse eventually leads to formal police complaints, but societal pressure heavily dilutes reporting rates.
- from: upi_and_bank_scams
  to: fir_registration
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: Victims of digital financial fraud must register cyber crime FIRs to attempt recovery of stolen funds.
- from: deepfake_and_identity_theft
  to: cyberbullying_and_trolling
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: Malicious actors use deepfakes and stolen identities to harass and troll victims online.
- from: deepfake_and_identity_theft
  to: upi_and_bank_scams
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Stolen digital identities are weaponized to bypass banking security and execute financial fraud.
- from: fir_registration
  to: criminal_litigation_risk
  weight: 0.95
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: The formal registration of an FIR initiates the legal process, directly increasing criminal litigation risk for the accused.
- from: police_response_time
  to: assault_and_battery
  weight: 0.70
  polarity: -1
  delay: IMMEDIATE
  reasoning: Faster police response times deter ongoing physical violence and reduce the severity of assaults.
- from: child_kidnapping
  to: fir_registration
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: The abduction of a child results in immediate FIR registration to trigger emergency police search protocols.
- from: street_harassment
  to: sexual_assault
  weight: 0.60
  polarity: 1
  delay: SHORT_TERM
  reasoning: Unchecked street harassment creates an unsafe environment that frequently escalates into physical sexual assault.
- from: stray_animals
  to: stray_animal_attacks
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: High populations of unmanaged stray dogs and cattle in urban areas directly cause physical attacks on pedestrians.
- from: street_waterlogging
  to: electrocution_hazard
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: Flooded streets submerge exposed electrical wires and transformer boxes, creating lethal electrocution risks.
- from: street_waterlogging
  to: road_traffic_accidents
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: Waterlogged roads obscure potholes and reduce vehicle traction, leading to severe traffic accidents.
- from: social_media_accounts
  to: cyberbullying_and_trolling
  weight: 0.75
  polarity: 1
  delay: IMMEDIATE
  reasoning: Increased presence on social media platforms exposes individuals to digital harassment and coordinated trolling.
- from: personal_data_privacy
  to: deepfake_and_identity_theft
  weight: 0.75
  polarity: -1
  delay: SHORT_TERM
  reasoning: Stronger personal data privacy controls reduce the availability of photos and information used by identity thieves.
- from: spam_calls
  to: upi_and_bank_scams
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Fraudulent telemarketing and spam calls serve as the primary delivery mechanism for UPI phishing scams.
- from: spam_calls
  to: investment_and_job_scams
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: Scammers use unsolicited calls and messages to lure victims into fake cryptocurrency and employment schemes.
- from: firecracker
  to: fire_hazards
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: The unregulated bursting of firecrackers during festivals directly ignites residential and commercial fires.
- from: community_gathering
  to: stampedes
  weight: 0.65
  polarity: 1
  delay: IMMEDIATE
  reasoning: Unmanaged large-scale community and religious gatherings create dangerous crowd densities prone to stampedes.
- from: aadhaar_authentication
  to: deepfake_and_identity_theft
  weight: 0.70
  polarity: -1
  delay: SHORT_TERM
  reasoning: Robust biometric Aadhaar authentication makes it significantly harder for criminals to successfully use fake identities.
- from: railway_accidents
  to: irctc_train_ticket
  weight: 0.85
  polarity: -1
  delay: SHORT_TERM
  reasoning: Train derailments and accidents force the cancellation of routes, negatively impacting IRCTC ticketing and travel plans.
- from: curfews_and_section_144
  to: street_food
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Imposed curfews force the immediate shutdown of street food stalls and night markets.
- from: curfews_and_section_144
  to: street_vendor_income
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Restrictions on public movement completely halt the daily operations and earnings of street vendors.
- from: curfews_and_section_144
  to: gig_worker_payouts
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: Section 144 and curfews block delivery personnel from operating, directly cutting off gig worker payouts.
- from: curfews_and_section_144
  to: offline_coaching_centers
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Public order emergencies force the physical closure of offline coaching centers and educational institutes.
- from: curfews_and_section_144
  to: cinema_ticket
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Curfews mandate the closure of entertainment venues, halting cinema ticket sales and movie screenings.
- from: investment_and_job_scams
  to: savings_account_balance
  weight: 0.85
  polarity: -1
  delay: SHORT_TERM
  reasoning: Victims of fake investment schemes transfer large sums of money, directly depleting their personal savings.
- from: vehicle_theft
  to: vehicle_insurance_premium
  weight: 0.70
  polarity: 1
  delay: LONG_TERM
  reasoning: High rates of vehicle theft in a region cause insurers to raise motor insurance premiums to cover increased claim risks.
- from: sexual_assault
  to: therapy_consultation
  weight: 0.70
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Survivors of sexual assault frequently require professional psychiatric therapy to process severe trauma.
- from: cyberbullying_and_trolling
  to: anxiety_disorders
  weight: 0.75
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Relentless online harassment and public shaming trigger acute anxiety disorders in victims.
- from: stray_animal_attacks
  to: doctor_consultation
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Dog bites and animal attacks require immediate outpatient doctor consultations for rabies vaccinations and wound care.
- from: riots_and_clashes
  to: public_park
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: Violent clashes render public parks and community spaces unsafe and inaccessible to citizens.
- from: particulate_matter_levels
  to: ambient_aqi
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: High concentrations of particulate matter directly and immediately increase the ambient Air Quality Index readings.
- from: particulate_matter_levels
  to: winter_smog
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Suspended particulate matter forms the primary physical component of dense winter smog.
- from: outdoor_cold
  to: winter_smog
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: Cold outdoor temperatures create thermal inversions that trap pollutants close to the ground, forming smog.
- from: outdoor_humidity
  to: winter_smog
  weight: 0.70
  polarity: 1
  delay: IMMEDIATE
  reasoning: High humidity provides moisture that combines with particulate matter to create thick smog.
- from: street_garbage
  to: stray_animals
  weight: 0.80
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Accumulated street garbage provides a direct food source that sustains stray animal populations in urban areas.
- from: street_garbage
  to: open_drains
  weight: 0.85
  polarity: -1
  delay: SHORT_TERM
  reasoning: Improperly disposed street garbage washes into and physically blocks open drainage systems.
- from: open_drains
  to: public_urination_odour
  weight: 0.75
  polarity: 1
  delay: IMMEDIATE
  reasoning: Exposed sewage in open drains compounds with public urination to create severe localized foul odours.
- from: open_drains
  to: stagnant_water_pools
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Blocked or overflowing open drains spill over to form stagnant water pools on streets.
- from: street_waterlogging
  to: stagnant_water_pools
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Receding street waterlogging leaves behind isolated pools of stagnant water in urban depressions.
- from: street_waterlogging
  to: basement_flooding
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Excess water from waterlogged streets cascades down into residential and commercial basements.
- from: urban_landfills
  to: polluted_surface_water
  weight: 0.80
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Toxic leachate from urban landfills seeps into and contaminates nearby surface water bodies.
- from: street_garbage
  to: urban_landfills
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Collected street garbage is transported to and physically expands urban landfills.
- from: neighborhood_greenery
  to: outdoor_heat
  weight: 0.70
  polarity: -1
  delay: LONG_TERM
  reasoning: Tree canopies and vegetation provide shade and evaporative cooling, reducing localized outdoor heat.
- from: neighborhood_greenery
  to: particulate_matter_levels
  weight: 0.60
  polarity: -1
  delay: LONG_TERM
  reasoning: Urban foliage acts as a physical filter, trapping airborne particulate matter on leaf surfaces.
- from: outdoor_heat
  to: polluted_surface_water
  weight: 0.65
  polarity: 1
  delay: SHORT_TERM
  reasoning: High outdoor heat accelerates evaporation in water bodies, concentrating existing pollutants and triggering algal blooms.
- from: firecracker
  to: particulate_matter_levels
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Combustion of firecrackers releases massive immediate spikes of heavy metals and particulate matter into the air.
- from: firecracker
  to: event_and_construction_noise
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Detonation of firecrackers generates acute, high-decibel noise pollution in residential neighborhoods.
- from: festive_idol
  to: polluted_surface_water
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Immersion of painted festive idols introduces synthetic colors, plaster of Paris, and heavy metals into local water bodies.
- from: particulate_matter_levels
  to: asthma
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Inhalation of fine particulate matter triggers severe inflammation and exacerbates asthma attacks.
- from: particulate_matter_levels
  to: copd
  weight: 0.85
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Chronic exposure to high particulate matter levels accelerates lung function decline and triggers COPD exacerbations.
- from: stagnant_water_pools
  to: dengue
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Stagnant water pools serve as the primary breeding ground for Aedes mosquitoes that transmit dengue fever.
- from: stagnant_water_pools
  to: malaria
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Anopheles mosquitoes breed in stagnant water pools, directly facilitating the spread of malaria.
- from: polluted_surface_water
  to: cholera_and_diarrhea
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Consumption of or contact with surface water polluted by fecal matter directly causes cholera and diarrheal infections.
- from: street_waterlogging
  to: food_delivery_payouts
  weight: 0.80
  polarity: -1
  delay: IMMEDIATE
  reasoning: Flooded streets physically prevent gig workers from completing deliveries, reducing their daily payouts.
- from: outdoor_heat
  to: residential_electricity
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Extreme outdoor heat drives massive surges in residential electricity consumption due to continuous air conditioner usage.
- from: outdoor_heat
  to: farm_labor_wages
  weight: 0.75
  polarity: -1
  delay: IMMEDIATE
  reasoning: Severe outdoor heat limits the safe working hours for agricultural laborers, reducing their daily wage earning capacity.
- from: outdoor_heat
  to: street_vendor_income
  weight: 0.75
  polarity: -1
  delay: IMMEDIATE
  reasoning: Intense daytime heat deters pedestrian footfall, directly reducing the daily sales and income of street vendors.
- from: stray_animals
  to: road_traffic_accidents
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: Stray animals wandering onto busy roads force sudden swerving and braking, directly causing road traffic accidents.
- from: ambient_aqi
  to: investment_property_value
  weight: 0.60
  polarity: -1
  delay: LONG_TERM
  reasoning: Consistently poor ambient AQI deters homebuyers, depressing the investment value of residential real estate in affected areas.
- from: neighborhood_greenery
  to: investment_property_value
  weight: 0.75
  polarity: 1
  delay: LONG_TERM
  reasoning: Proximity to well-maintained neighborhood greenery and parks commands a premium, increasing local property values.
- from: basement_flooding
  to: repair_service_charges
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Inundation of basements necessitates immediate hiring of water extraction and structural repair services.
- from: basement_flooding
  to: vehicle_servicing_cost
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Vehicles submerged during basement flooding suffer severe engine and electrical damage, requiring expensive servicing.
- from: open_drains
  to: pest_control_services
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: Open drains harbor massive populations of roaches and rodents, driving nearby residents to hire pest control services.
- from: traffic_noise
  to: investment_property_value
  weight: 0.60
  polarity: -1
  delay: LONG_TERM
  reasoning: High levels of continuous traffic noise make residential properties less desirable, lowering their market value.
- from: outdoor_cold
  to: residential_electricity
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Severe outdoor cold waves trigger widespread use of electric room heaters, spiking residential electricity demand.
- from: smartphone_device
  to: whatsapp_messaging
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: WhatsApp messaging strictly requires a smartphone device to be installed and operated by the user.
- from: smartphone_device
  to: social_media_accounts
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Active participation and content creation for social media accounts heavily depend on smartphone access.
- from: smartphone_device
  to: upi_transaction_success
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Initiating a UPI transaction requires a smartphone device to scan QR codes or use payment apps.
- from: digital_payment_infrastructure
  to: upi_transaction_success
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: The success rate of UPI transactions depends entirely on the uptime of the underlying digital payment infrastructure.
- from: internet_shutdowns
  to: mobile_network_quality
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Government-mandated internet shutdowns physically halt mobile network data transmission.
- from: internet_shutdowns
  to: broadband_network_quality
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: Regional internet blackouts frequently disrupt fixed broadband network quality and connectivity.
- from: internet_shutdowns
  to: whatsapp_messaging
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Internet shutdowns immediately block users from sending or receiving WhatsApp messages.
- from: internet_shutdowns
  to: upi_transaction_success
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Without internet access during shutdowns, digital UPI transactions fail to process.
- from: aadhaar_authentication
  to: digilocker_documents
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Accessing and verifying official documents in DigiLocker strictly requires Aadhaar authentication.
- from: aadhaar_authentication
  to: epramaan_and_sso
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Government Single Sign-On (SSO) services rely heavily on Aadhaar authentication to verify citizen identity.
- from: aadhaar_authentication
  to: pan_aadhaar_linkage
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: The process of linking a PAN card inherently requires a valid Aadhaar authentication.
- from: aadhaar_authentication
  to: e_mandate_autopay
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Setting up digital e-mandates often requires Aadhaar-based eSign for authorization.
- from: data_breaches_and_leaks
  to: spam_calls
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: Leaked personal phone numbers are acquired by telemarketers to generate massive volumes of spam calls.
- from: data_breaches_and_leaks
  to: personal_data_privacy
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: Data breaches directly compromise and disrupt an individual's personal data privacy.
- from: mobile_data_tariff
  to: fiber_broadband_tariff
  weight: 0.65
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Cheap mobile data plans compete directly with fixed fiber broadband subscriptions, causing their prices to move together.
- from: public_wifi
  to: mobile_data_tariff
  weight: 0.50
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: Widespread availability of free public Wi-Fi reduces consumer reliance on paid mobile data, putting downward pressure on tariffs.
- from: upi_transaction_limits
  to: upi_transaction_success
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: Daily transaction limits imposed by banks cause high-value UPI transactions to fail.
- from: digital_payment_infrastructure
  to: e_mandate_autopay
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Recurring e-mandates depend entirely on the continuous operation of the digital payment infrastructure to process auto-debits.
- from: upi_and_bank_scams
  to: upi_transaction_limits
  weight: 0.80
  polarity: -1
  delay: SHORT_TERM
  reasoning: A rise in banking scams prompts financial institutions to lower UPI transaction limits to mitigate fraud.
- from: cyberbullying_and_trolling
  to: content_moderation_policies
  weight: 0.80
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Widespread cyberbullying forces platforms to produce and enforce stricter content moderation policies.
- from: rwa_regulation
  to: fiber_broadband_tariff
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: Resident Welfare Associations often negotiate exclusive ISP contracts, driving up the fiber broadband tariffs available to residents.
- from: it_sector_jobs
  to: laptop_computer
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: IT sector employment provides the income and corporate allowances that fund the purchase of laptop computers.
- from: riots_and_clashes
  to: internet_shutdowns
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: Severe civil unrest and riots often prompt authorities to impose localized internet shutdowns to control information flow.
- from: smartphone_device
  to: food_delivery_services
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Consumers cannot order from modern app-based food delivery platforms without a smartphone device.
- from: smartphone_device
  to: cab_aggregator_fare
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Booking a ride and paying the cab aggregator fare strictly requires a smartphone device.
- from: smartphone_device
  to: food_delivery_payouts
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Gig workers depend entirely on smartphone devices to receive orders and earn food delivery payouts.
- from: smartphone_device
  to: cab_driver_earnings
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Cab drivers rely entirely on smartphone devices to connect with riders and generate earnings.
- from: pan_aadhaar_linkage
  to: personal_income_tax
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: Filing personal income tax returns legally requires the linkage of PAN and Aadhaar cards.
- from: data_breaches_and_leaks
  to: upi_and_bank_scams
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: Leaked financial data and personal identifiers are used by fraudsters to execute UPI and bank scams.
- from: data_breaches_and_leaks
  to: deepfake_and_identity_theft
  weight: 0.85
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: Stolen personal photos and data from breaches are utilized to produce deepfakes and commit identity theft.
- from: broadband_network_quality
  to: ott_subscription
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: High-definition streaming via OTT subscriptions depends heavily on reliable broadband network quality.
- from: laptop_computer
  to: video_game
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: Playing modern PC video games strictly depends on having a capable laptop or desktop computer.
- from: aadhaar_authentication
  to: mgnrega_wages
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: The Aadhaar-Based Payment System (ABPS) is mandatory for crediting MGNREGA rural wages to workers.
- from: digilocker_documents
  to: traffic_fines
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: Presenting valid digital driving licenses via DigiLocker legally prevents the issuance of traffic fines for missing documents.
- from: upi_transaction_success
  to: temple_donation
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: Successful UPI transactions via QR codes directly fund digital temple donations.
- from: social_media_accounts
  to: fine_dining_restaurants
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: Viral food reviews and aesthetic posts on social media accounts drive significant footfall to fine dining restaurants.
```
