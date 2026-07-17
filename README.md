# srishtimaurya_PBEL3.0


## About the Project

This project is an AI-based Resume Screening and Ranking System that analyzes resumes against job descriptions and ranks candidates based on relevance.

## Testing Files

This repository includes 5 sample resumes and 5 sample job descriptions for testing the system. See details below:

- Resumes: `sample_resumes/`
- Job Descriptions: `sample_job_descriptions/`

### Resume–JD Mapping (Test Cases)


This mapping includes both matching and intentionally mismatched cases to verify that the model correctly ranks relevant resumes higher and irrelevant ones lower.


 Sample_Resume_1_DataScientist.pdf ---> jd_1_data_scientist.txt ----> Match 
 Sample_Resume_2_NLP_MLEngineer.pdf ----> jd_2_ml_engineer.txt ---> Match 
 Sample_Resume_3_DataAnalyst.pdf ----> jd_3_backend_java_developer.txt ---> Mismatch (intentional) 
 Sample_Resume_4_ComputerVisionIntern.pdf---> jd_4_computer_vision_intern.txt ---> Match 
 Sample_Resume_5_JuniorPythonDeveloper.pdf ---> jd_5_frontend_web_developer.txt ----> Mismatch (intentional) 
