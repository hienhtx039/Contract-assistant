"""
Generate tailored interview questions from CV using the configured LLM provider.
Questions follow GreenNode's assessment framework and question bank.
"""
import io
import json
import logging

import PyPDF2
import docx

from interview.llm_client import call_llm


QUESTION_PROMPT = """Bạn là chuyên gia tuyển dụng của GreenNode. Dựa trên CV ứng viên và vị trí ứng tuyển, hãy tạo bộ câu hỏi phỏng vấn bằng TIẾNG VIỆT theo đúng framework đánh giá của GreenNode.

## Vị trí ứng tuyển
{position}

## Mô tả công việc (JD)
{jd_text}

## CV ứng viên
{cv_text}

## Framework đánh giá GreenNode (9 tiêu chí)

### 1. Capability — Functional Skills (3 câu hỏi)
Tạo 3 câu hỏi kỹ thuật/chuyên môn DỰA TRÊN kinh nghiệm trong CV VÀ yêu cầu trong JD. Mỗi câu hỏi phải:
- Liên quan trực tiếp đến một kỹ năng/dự án cụ thể trong CV
- Đánh giá mức độ phù hợp với yêu cầu JD (nếu có JD)
- Có câu hỏi follow-up để đào sâu
- Nếu có gap giữa CV và JD, tạo câu hỏi để kiểm tra khả năng học hỏi

### 2. Capability — GreenNode's DNA (3 câu hỏi)
- Collaboration: Hỏi về cách ứng viên hợp tác trong các dự án được nêu trong CV
- Continuous Learning & Improvement: Hỏi về cách ứng viên học hỏi và phát triển
- Customer Centric: Hỏi về cách ứng viên tập trung vào người dùng/khách hàng

### 3. Motivation (3 câu hỏi)
- WHO YOU ARE (Bạn là ai): Giá trị, tính cách, phong cách làm việc
- HOW YOU THINK (Cách bạn suy nghĩ): Giải quyết vấn đề, xử lý sự mơ hồ
- WHAT YOU COMMIT (Bạn cam kết gì): Động lực apply, kỳ vọng, cam kết

## Ngân hàng câu hỏi tham khảo (dùng làm gợi ý, PHẢI tùy chỉnh theo CV)

### WHO YOU ARE
- Kể về một lần bạn nhận ra mình đã làm sai — dù không ai phát hiện. Bạn đã làm gì sau đó?
- Có bao giờ bạn không đồng ý với quyết định của nhóm không? Bạn đã xử lý thế nào?
- Kể về giai đoạn bận rộn nhất bạn từng trải qua. Bạn đã sắp xếp như thế nào?
- Bạn nhận feedback tốt nhất theo cách nào? Kể một ví dụ.

### HOW YOU THINK
- Kể về một vấn đề bạn gặp mà lúc đầu không biết bắt đầu từ đâu. Bước đầu tiên bạn làm là gì?
- Có bao giờ bạn phải đưa ra quyết định mà không có đủ thông tin không?
- Kể về lần bạn thử một cách làm mới — dù không chắc nó hiệu quả.
- Kể về lần bạn phát hiện ra mình đang làm sai hướng. Bạn đã xử lý thế nào?
- Bạn thường nhờ giúp đỡ sớm hay cố tự xử lý trước?

### WHAT YOU COMMIT
- Tại sao bạn apply vị trí này? Bạn đã cân nhắc những lựa chọn nào khác?
- Bạn biết gì về công việc thực tế trong vị trí này?
- Trong vòng 1 năm tới bạn muốn làm gì?
- Kể về một cam kết bạn đã giữ dù giữa chừng muốn bỏ.
- Nếu sau 2–3 tuần đầu công việc khác nhiều so với kỳ vọng — bạn sẽ làm gì?

## Yêu cầu đầu ra
Trả về CHỈ JSON hợp lệ. Mỗi câu hỏi phải có câu hỏi chính và câu hỏi follow-up. Tất cả bằng TIẾNG VIỆT.
{{
  "candidate_summary": "<tóm tắt ngắn 2-3 câu về ứng viên dựa trên CV>",
  "functional_skills": [
    {{
      "skill_area": "<lĩnh vực kỹ năng từ CV>",
      "main_question": "<câu hỏi chính>",
      "follow_up": "<câu hỏi follow-up để đào sâu>",
      "what_to_look_for": "<gợi ý cho người phỏng vấn: tìm kiếm điều gì trong câu trả lời>"
    }},
    {{
      "skill_area": "<lĩnh vực kỹ năng từ CV>",
      "main_question": "<câu hỏi chính>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }},
    {{
      "skill_area": "<lĩnh vực kỹ năng từ CV>",
      "main_question": "<câu hỏi chính>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }}
  ],
  "greennode_dna": [
    {{
      "criterion": "Collaboration",
      "main_question": "<câu hỏi về hợp tác, liên quan đến dự án trong CV>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }},
    {{
      "criterion": "Continuous Learning & Improvement",
      "main_question": "<câu hỏi về học hỏi>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }},
    {{
      "criterion": "Customer Centric",
      "main_question": "<câu hỏi về khách hàng/người dùng>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }}
  ],
  "motivation": [
    {{
      "criterion": "WHO YOU ARE",
      "main_question": "<câu hỏi về giá trị, tính cách>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }},
    {{
      "criterion": "HOW YOU THINK",
      "main_question": "<câu hỏi về giải quyết vấn đề>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }},
    {{
      "criterion": "WHAT YOU COMMIT",
      "main_question": "<câu hỏi về cam kết, động lực>",
      "follow_up": "<câu hỏi follow-up>",
      "what_to_look_for": "<gợi ý>"
    }}
  ]
}}
"""


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract text from PDF or DOCX file."""
    lower = filename.lower()

    if lower.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()

    elif lower.endswith(".docx"):
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore").strip()

    else:
        raise ValueError(f"Unsupported file format: {filename}. Use PDF, DOCX, or TXT.")


def generate_questions(cv_text: str, position: str, jd_text: str = "", timeout: int = 120) -> dict:
    """
    Generate interview questions from CV + JD using Claude Code CLI.

    Args:
        cv_text: Extracted text from CV.
        position: Position the candidate is applying for.
        jd_text: Optional job description text.
        timeout: Max seconds to wait.

    Returns:
        Parsed questions dict, or error dict on failure.
    """
    jd_display = jd_text.strip() if jd_text.strip() else "(Không có JD - tạo câu hỏi dựa trên CV và vị trí)"
    prompt = QUESTION_PROMPT.format(cv_text=cv_text, position=position, jd_text=jd_display)

    output = ""
    try:
        output = call_llm(prompt, timeout=timeout)

        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()

        return json.loads(output)

    except TimeoutError:
        return {"error": "Question generation timed out"}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON: {e}")
        return {"error": f"Invalid JSON from LLM: {str(e)}", "raw_output": output[:2000]}
    except RuntimeError as e:
        logging.error(f"LLM call failed: {e}")
        return {"error": str(e)}
