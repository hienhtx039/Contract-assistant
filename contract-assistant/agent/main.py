"""GreenNode Contract Guardian agent and tools."""

import json
import os
from typing import Any

from interview.llm_client import call_llm

SYSTEM_PROMPT = (
    "Bạn là Chuyên gia Thẩm định Hợp đồng kỳ cựu. Nhiệm vụ của bạn là đọc nội dung Hợp đồng cung ứng dịch vụ, "
    "phân tích rủi ro theo 3 góc độ: Pháp lý, Tài chính, Thẩm định đối tác và hỗ trợ trả lời câu hỏi của người dùng."
)


def extract_contract_risks(contract_text: str) -> str:
    prompt = (
        "Hãy đóng vai Chuyên gia Tài chính & Pháp lý. Phân tích hợp đồng cung ứng dịch vụ sau và bóc tách các rủi ro, số liệu. "
        "BẠN PHẢI TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON (Tuyệt đối không bọc trong markdown hoặc giải thích gì thêm) với cấu trúc như sau:\n"
        "{\n"
        '  "summary": "Tóm tắt ngắn gọn nội dung và tính chất hợp đồng",\n'
        '  "legal_risks": [{"group": "Tên nhóm (vd: Thanh toán, Chấm dứt)", "severity": "Vàng hoặc Đỏ", "issue": "Tên vấn đề", "risk": "Mô tả chi tiết rủi ro", "suggestion": "Đề xuất sửa đổi"}],\n'
        '  "financial_risks": [{"risk": "Tên rủi ro tài chính", "description": "Mô tả rủi ro tài chính"}],\n'
        '  "yellow_warnings": [{"warning": "Tiêu đề cảnh báo", "description": "Mô tả điểm cần thận trọng"}],\n'
        '  "negotiation_points": [{"point": "Điểm cần đàm phán", "suggestion": "Đề xuất đàm phán cụ thể"}],\n'
        '  "total_value": "Trích xuất tổng giá trị hợp đồng (vd: 1.000.000.000 VND hoặc Chưa điền)",\n'
        '  "working_capital_gap": "Phân tích khoảng hụt vốn lưu động dựa trên thanh toán (vd: Rủi ro đọng vốn 45 ngày)",\n'
        '  "dso_estimate": "Ước tính số ngày thu tiền bình quân (DSO) (vd: 45 ngày kể từ nghiệm thu)",\n'
        '  "cashflow_table": [{"Kỳ": "Tên đợt (vd: Đợt 1)", "Giá trị": "Số tiền/Tỷ lệ", "Ghi chú": "Điều kiện để được thanh toán đợt này"}]\n'
        "}\n\n"
        f"\n\nHợp đồng:\n{contract_text}"
    )
    return call_llm(prompt, timeout=180)


def check_compliance_mock(company_name: str) -> str:
    # Gọi LLM sinh ra báo cáo thẩm định (Due Diligence) cho đối tác
    prompt = (
        f"Bạn là Hệ thống Kiểm tra Tuân thủ & Trừng phạt kinh tế (Compliance Checker). "
        f"Hãy thực hiện rà soát thông tin rủi ro giả định cho đối tác có tên: '{company_name}'. "
        "Vì dữ liệu định danh có thể chưa đầy đủ, hãy sinh ra một báo cáo đánh giá mang tính thận trọng và chuyên nghiệp. "
        "TRẢ VỀ DUY NHẤT MỘT CHUỖI JSON HỢP LỆ (Không giải thích thêm) với cấu trúc chính xác như sau:\n"
        "{\n"
        f'  "company_name": "{company_name}",\n'
        '  "partner_status": "Trạng thái (vd: Vàng - Thận trọng / Đỏ - Rủi ro cao)",\n'
        '  "ky_luat_peps": "Mô tả kết quả rà soát danh sách đen, cấm vận quốc tế hoặc PEPs...",\n'
        '  "conflict_of_interest": "Phân tích rủi ro hối lộ, xung đột lợi ích nội bộ...",\n'
        '  "history": {"previous_contracts": 0, "incidents": 0},\n'
        '  "recommendation": "Đề xuất hành động tiếp theo cho bộ phận phê duyệt hợp đồng..."\n'
        "}"
    )
    return call_llm(prompt, timeout=180)


def generate_negotiation_email(risk_points: str) -> str:
    prompt = (
        "Bạn là chuyên gia đàm phán hợp đồng. Dựa trên các rủi ro sau, hãy viết email tiếng Việt chuyên nghiệp, "
        "lịch sự nhưng rõ ràng, yêu cầu đối tác đàm phán lại các điều khoản bất lợi. "
        "Chỉ trả về nội dung email, không giải thích.\n\nRủi ro:\n"
        f"{risk_points}"
    )
    return call_llm(prompt, timeout=180)


def _read_contract_bytes(uploaded_file: Any) -> str:
    name = (getattr(uploaded_file, "name", None) or getattr(uploaded_file, "filename", "file")).lower()
    data = uploaded_file.read()

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        import io
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if name.endswith(".docx"):
        import io
        import docx

        document = docx.Document(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())

    return data.decode("utf-8", errors="ignore")


def run_agent(contract_text: str, question: str = "") -> str:
    prompt = (
        f"System prompt: {SYSTEM_PROMPT}\n\n"
        f"Nội dung hợp đồng:\n{contract_text}\n\n"
        f"Câu hỏi người dùng: {question or 'Hãy phân tích tổng quan hợp đồng.'}"
    )
    return call_llm(prompt, timeout=180)


if __name__ == "__main__":
    sample = os.environ.get("CONTRACT_TEXT", "")
    if sample:
        print(run_agent(sample))