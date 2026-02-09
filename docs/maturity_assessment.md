# CMMI Maturity Assessment

The Maturity module allows organizations to assess their implementation of standard controls (ISO 27002, NIST, etc.) against the **Capability Maturity Model Integration (CMMI)** framework.

## WORKFLOW

1.  **Select Control**: Navigate to the Maturity Dashboard to see a list of all controls and their current maturity status.
2.  **Assess**: Click "Assess" on a specific control.
3.  **Evidence Collection**: linking to policy documents, logs, or other evidence, answer the specific requirements for each maturity level.
4.  **Scoring**: The system automatically calculates the achieved maturity level based on your answers.

## SCORING LOGIC

The CMMI maturity levels are hierarchical. To achieve a higher level, **all constraints of the lower levels must also be met**.

| Level | Name | Requirement |
| :--- | :--- | :--- |
| **1** | **Initial** | Default state. Processes are ad-hoc and chaotic. |
| **2** | **Managed** | All Level 2 requirements are compliant. |
| **3** | **Defined** | All Level 2 **AND** Level 3 requirements are compliant. |
| **4** | **Quantitatively Managed** | All Level 2, 3, **AND** 4 requirements are compliant. |
| **5** | **Optimizing** | All Level 2, 3, 4, **AND** 5 requirements are compliant. |

### Example

If you mark all Level 3 requirements as `Compliant` but miss one requirement in Level 2, your resulting score will be **Level 1 (Initial)** because the foundation (Level 2) is not solid.

## REQUIREMENTS

### Level 2: Managed
Focuses on basic project management controls.
- Is the process planned and executed in accordance with policy?
- Are skilled people providing adequate resources?
- Is the process monitored and controlled?

### Level 3: Defined
Focuses on process standardization across the organization.
- Is the process tailored from standard processes?
- Is the process maintained and improved?
- Are experiences contributed back to the organizational assets?

### Level 4: Quantitatively Managed
Focuses on numeric tracking and statistical management.
- Are quantitative objectives established?
- Is the process statistically managed?
- Can performance be predicted?

### Level 5: Optimizing
Focuses on continuous process improvement.
- Are improvements based on quantitative understanding?
- Is continuous improvement enabled by feedback?
- Are improvement effects measured?
