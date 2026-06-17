"""
Interview assessment using the configured LLM provider (Claude CLI or GreenNode MaaS).
Sends transcript + GreenNode rubric to the LLM and parses structured JSON.
"""
import json
import logging

from interview.llm_client import call_llm


ASSESSMENT_PROMPT = """Bạn là người đánh giá phỏng vấn cho GreenNode. Phân tích bản ghi phỏng vấn dưới đây và đưa ra đánh giá có cấu trúc. TẤT CẢ nội dung đánh giá phải viết bằng TIẾNG VIỆT.

## Hướng dẫn chấm điểm (thang 1-5)
- 5 (Xuất sắc): Tự chủ dẫn dắt; có bằng chứng/số liệu rõ ràng; lường trước rủi ro; tác động đến các bên liên quan; phương pháp lặp lại được.
- 4 (Trên kỳ vọng): Bằng chứng tốt; còn thiếu sót nhỏ; xử lý được vấn đề phức tạp với ít hỗ trợ; có cấu trúc và tinh thần trách nhiệm.
- 3 (Đạt kỳ vọng): Năng lực cơ bản; thực hiện được với hướng dẫn; bằng chứng hạn chế nhưng đáng tin; độ phức tạp trung bình.
- 2 (Dưới kỳ vọng): Thụ động; bằng chứng hời hợt; phương pháp không nhất quán; phụ thuộc nhiều vào người khác; ít tiếp xúc với vấn đề phức tạp.
- 1 (Yếu / Không thể hiện): Không có ví dụ liên quan; vai trò/tác động không rõ ràng; hiểu sai vấn đề; không diễn đạt được cách tiếp cận.

## Các hạng mục đánh giá

### Năng lực — Kỹ năng chuyên môn (3 tiêu chí)
Nếu có JD: Chấm điểm 3 kỹ năng quan trọng nhất TRONG JD dựa trên câu trả lời của ứng viên. Nếu ứng viên không thể hiện kỹ năng yêu cầu trong JD, cho điểm thấp.
Nếu không có JD: Xác định và chấm điểm 3 lĩnh vực kỹ năng nổi bật nhất từ buổi phỏng vấn.

### Năng lực — DNA của GreenNode (3 tiêu chí)
- Collaboration (Hợp tác): Ứng viên thể hiện khả năng làm việc nhóm và phối hợp với người khác như thế nào?
- Continuous Learning & Improvement (Học hỏi & Cải tiến liên tục): Ứng viên có thể hiện tư duy phát triển và mong muốn học hỏi không?
- Customer Centric (Lấy khách hàng làm trung tâm): Ứng viên có thể hiện sự tập trung vào nhu cầu của khách hàng/người dùng không?

### Động lực (3 tiêu chí)
- WHO YOU ARE (BẠN LÀ AI): Giá trị, tính cách, sự chính trực, phong cách làm việc dưới áp lực. Các câu hỏi về sự trung thực, xử lý bất đồng, quản lý deadline, tiếp nhận phản hồi.
- HOW YOU THINK (CÁCH BẠN SUY NGHĨ): Khả năng giải quyết vấn đề, xử lý sự mơ hồ, ra quyết định với thông tin không đầy đủ, biết khi nào cần thay đổi hướng, khi nào cần nhờ giúp đỡ.
- WHAT YOU COMMIT (BẠN CAM KẾT GÌ): Sự chủ đích trong lựa chọn nghề nghiệp, theo đuổi cam kết đến cùng, khả năng phục hồi, rõ ràng về kỳ vọng.

## Quy tắc quyết định
- Điểm trung bình 9 tiêu chí >= 3.0 -> HIRE (Tuyển)
- Điểm trung bình 9 tiêu chí >= 2.5 -> CONSIDER (Cân nhắc)
- Điểm trung bình 9 tiêu chí < 2.5 -> NOT PROCEED (Không tuyển)

## Mô tả công việc (JD)
{jd_text}

## Bản ghi phỏng vấn
{transcript}

## Yêu cầu đầu ra
Trả về CHỈ JSON hợp lệ (không có markdown fences, không có giải thích trước/sau). Tất cả nội dung text trong JSON phải bằng TIẾNG VIỆT. Sử dụng đúng cấu trúc sau:
{{
  "functional_skills": [
    {{"criterion": "<tên lĩnh vực kỹ năng>", "question_asked": "<câu hỏi liên quan từ bản ghi>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn từ bản ghi>"}},
    {{"criterion": "<tên lĩnh vực kỹ năng>", "question_asked": "<câu hỏi liên quan từ bản ghi>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn từ bản ghi>"}},
    {{"criterion": "<tên lĩnh vực kỹ năng>", "question_asked": "<câu hỏi liên quan từ bản ghi>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn từ bản ghi>"}}
  ],
  "greennode_dna": [
    {{"criterion": "Collaboration", "question_asked": "<câu hỏi liên quan>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn bằng tiếng Việt>"}},
    {{"criterion": "Continuous Learning & Improvement", "question_asked": "<câu hỏi liên quan>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn bằng tiếng Việt>"}},
    {{"criterion": "Customer Centric", "question_asked": "<câu hỏi liên quan>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn bằng tiếng Việt>"}}
  ],
  "motivation": [
    {{"criterion": "WHO YOU ARE", "question_asked": "<câu hỏi liên quan>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn bằng tiếng Việt>"}},
    {{"criterion": "HOW YOU THINK", "question_asked": "<câu hỏi liên quan>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn bằng tiếng Việt>"}},
    {{"criterion": "WHAT YOU COMMIT", "question_asked": "<câu hỏi liên quan>", "score": <1-5>, "evidence": "<bằng chứng ngắn gọn bằng tiếng Việt>"}}
  ],
  "total_score": <điểm trung bình 9 tiêu chí, 1 số thập phân>,
  "recommendation": "<HIRE|CONSIDER|NOT PROCEED>",
  "summary": "<đánh giá tổng quan 2-3 câu bằng tiếng Việt>"
}}
"""


def assess_transcript(transcript: str, jd_text: str = "", timeout: int = 120) -> dict:
    """
    Send transcript to Claude Code CLI for assessment.

    Args:
        transcript: Full interview transcript text.
        jd_text: Optional job description text for functional skills assessment.
        timeout: Max seconds to wait for Claude response.

    Returns:
        Parsed assessment dict, or error dict on failure.
    """
    jd_display = jd_text.strip() if jd_text.strip() else "(Không có JD - đánh giá dựa trên nội dung phỏng vấn)"
    prompt = ASSESSMENT_PROMPT.format(transcript=transcript, jd_text=jd_display)

    output = ""
    try:
        output = call_llm(prompt, timeout=timeout)

        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()

        return json.loads(output)

    except TimeoutError:
        logging.error("LLM timed out during assessment")
        return {"error": "Assessment timed out"}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM output as JSON: {e}")
        return {"error": f"Invalid JSON from LLM: {str(e)}", "raw_output": output[:2000]}
    except RuntimeError as e:
        logging.error(f"LLM call failed: {e}")
        return {"error": str(e)}
