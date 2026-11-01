-- The whole patient chart, governed record by record: visits, notes, medications and imaging, read live from each
-- branch system (and the PACS on S3), and shown only for the records the caller may open right now (HEALTH_GOV.VISIBLE:
-- standing access, or an active ticket). A ticket therefore opens a patient's ENTIRE record at that branch, scans included,
-- and closes all of it when it runs out.

-- Identity as each branch recorded it. Name, birth date and mobile only with full-identity access.
CREATE OR REPLACE VIEW HEALTH_GOV.PATIENT_IDENTITY AS
SELECT r.RECORD_ID AS RECORD_KEY, m.UNIFIED_ID, r.BRANCH, r.SOURCE_SYSTEM, v.TICKET,
       CASE WHEN v.PHI_RANK = 2 THEN r.RECORD_ID END AS RECORD_ID,
       CASE WHEN v.PHI_RANK = 2 THEN r.NAME_AS_RECORDED END AS NAME_AS_RECORDED,
       CASE WHEN v.PHI_RANK = 2 THEN r.BIRTH_DATE_AS_RECORDED END AS BIRTH_DATE_AS_RECORDED,
       CASE WHEN v.PHI_RANK = 2 THEN r.MOBILE END AS MOBILE, r.SEX, YEAR(r.BIRTH_DATE) AS BIRTH_YEAR
FROM HOSP_CORE.PATIENT_RECORDS r JOIN HOSP_CORE.MPI m ON m.RECORD_ID = r.RECORD_ID
JOIN HEALTH_GOV.VISIBLE v ON v.RECORD_ID = r.RECORD_ID
COMMENT IS 'Grain: one row per record the caller may open. Identity fields are NULL without full-identity access.';

CREATE OR REPLACE VIEW HEALTH_GOV.ENCOUNTERS AS
SELECT e.UNIFIED_ID, e.ENCOUNTER_ID, e.BRANCH, e.SOURCE_SYSTEM, e.ENCOUNTER_CLASS, e.DEPARTMENT, e.ADMIT_DATE, e.DISCHARGE_DATE,
       e.STATUS, e.DX_CODE, e.DIAGNOSIS, v.TICKET
FROM HOSP_CORE.ENCOUNTERS e JOIN HEALTH_GOV.VISIBLE v ON v.RECORD_ID = e.RECORD_ID
COMMENT IS 'Grain: one row per visit or admission, from every branch system, read live; only the records the caller may open. TICKET names the ticket that opened the record (NULL = standing access).';

-- Clinical notes, read live from where they are written: discharge summaries in the legacy HIS (Postgres),
-- admission notes in the modern EHR (MongoDB). The text never leaves its source system except into this answer.
CREATE OR REPLACE VIEW HEALTH_GOV.NOTES AS
WITH n AS (
  SELECT v.PAT_NO AS RECORD_ID, s.VISIT_NO AS ENCOUNTER_ID, 'Discharge summary' AS NOTE_TYPE,
         TO_DATE(v.ADM_DT, 'DD/MM/YYYY') AS NOTE_DATE, s.SUMM_TXT AS NOTE_TEXT
  FROM HOSP_LEGACY.DIS_SUMM s JOIN HOSP_LEGACY.VISIT_HDR v ON v.VISIT_NO = s.VISIT_NO
  UNION ALL
  SELECT e."patientId", e."_id", 'Admission note', CAST(SUBSTR(e."admitted", 1, 10) AS DATE), e."note"
  FROM HOSP_EHR_ENCOUNTERS.ENCOUNTERS e WHERE e."note" IS NOT NULL)
SELECT m.UNIFIED_ID, r.BRANCH, r.SOURCE_SYSTEM, n.NOTE_TYPE, n.NOTE_DATE, n.NOTE_TEXT, v.TICKET
FROM n JOIN HEALTH_GOV.VISIBLE v ON v.RECORD_ID = n.RECORD_ID
JOIN HOSP_CORE.MPI m ON m.RECORD_ID = n.RECORD_ID JOIN HOSP_CORE.PATIENT_RECORDS r ON r.RECORD_ID = n.RECORD_ID
COMMENT IS 'Grain: one row per clinical note (discharge summary or admission note), read live from the branch system; only the records the caller may open.';

CREATE OR REPLACE VIEW HEALTH_GOV.MEDICATIONS AS
SELECT o.UNIFIED_ID, r.BRANCH, o.SOURCE_SYSTEM, o.ENCOUNTER_ID, o.DRUG, o.DOSE, o.ORDER_STATUS, o.DRUG_CLASS, v.TICKET
FROM HOSP_CORE.MEDICATIONS o JOIN HEALTH_GOV.VISIBLE v ON v.RECORD_ID = o.RECORD_ID
JOIN HOSP_CORE.PATIENT_RECORDS r ON r.RECORD_ID = o.RECORD_ID
COMMENT IS 'Grain: one row per medication order, any status, from every branch system; only the records the caller may open.';

-- Imaging: the PACS header index on S3, read in place. S3_KEY is the object key of the DICOM file. A caller who may not
-- open the record does not get the key, so no link to the image can be made for them.
CREATE OR REPLACE VIEW HEALTH_GOV.IMAGING AS
SELECT i.UNIFIED_ID, r.BRANCH, i.STUDY_DATE, i.MODALITY, i.BODY_PART, i.STUDY_DESCRIPTION, i.ACCESSION_NUMBER,
       i.S3_KEY, i.THUMB_KEY, i.FILE_BYTES, v.TICKET
FROM HOSP_CORE.IMAGING_STUDIES i JOIN HEALTH_GOV.VISIBLE v ON v.RECORD_ID = i.RECORD_ID
JOIN HOSP_CORE.PATIENT_RECORDS r ON r.RECORD_ID = i.RECORD_ID
COMMENT IS 'Grain: one row per imaging study (X-ray, CT, MRI) in the PACS on Amazon S3, for the records the caller may open. S3_KEY / THUMB_KEY locate the DICOM file and its preview; the pixels stay in S3.';

GRANT SELECT ON HEALTH_GOV.PATIENT_IDENTITY TO HC_CLINICIAN, HC_ANALYST;
GRANT SELECT ON HEALTH_GOV.ENCOUNTERS TO HC_CLINICIAN, HC_ANALYST;
GRANT SELECT ON HEALTH_GOV.NOTES TO HC_CLINICIAN;
GRANT SELECT ON HEALTH_GOV.MEDICATIONS TO HC_CLINICIAN, HC_ANALYST;
GRANT SELECT ON HEALTH_GOV.IMAGING TO HC_CLINICIAN;
