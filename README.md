Rà soát hợp đồng dịch vụ thủ công tốn nhiều giờ, dễ bỏ sót rủi ro và phụ thuộc vào chuyên môn cá nhân. Đội pháp lý và tài chính phải đọc từng trang, tra cứu từng điều khoản và tổng hợp ý kiến qua nhiều vòng — chậm, tốn nguồn lực và khó chuẩn hóa.

Người dùng

Nhân viên pháp lý, tài chính và procurement tại VNG— những người cần đánh giá nhanh hợp đồng trước khi phê duyệt nhưng không phải lúc nào cũng có đủ thời gian hoặc chuyên môn sâu về từng lĩnh vực.

Giá trị mang lại

Contract Assistant tự động phân tích hợp đồng chỉ trong vài phút: trích xuất rủi ro pháp lý, phân tích tài chính (DSO, working capital gap, dòng tiền), thẩm định đối tác, soạn email đàm phán và hỏi đáp tự do về bất kỳ điều khoản nào.

 Kết quả: rút ngắn thời gian rà soát từ vài giờ xuống vài phút, chuẩn hóa quy trình theo khung thống nhất, và giúp người không chuyên pháp lý chủ động đàm phán thay vì chỉ ký và chờ phát sinh vấn đề.



Tech Stack
Frontend: Streamlit (Python) — UI web app cho upload hợp đồng, hiển thị phân tích, chat
Backend / Agent:

Python 3.10
OpenAI SDK (client gọi LLM qua API tương thích OpenAI)
PyPDF2 + python-docx — parse hợp đồng PDF/DOCX
pandas — xử lý dữ liệu bảng

LLM / AI:

GreenNode MaaS (AI Platform HCM) — hosted LLM
Model: google/gemma-4-31b-it (phân tích hợp đồng)
Model: openai/whisper-large-v3 (transcription)

Infrastructure:

Docker — containerization
nginx — reverse proxy (port 8080), health check endpoint
supervisord — process manager (nginx + Streamlit)
GreenNode AgentBase — managed runtime, autoscaling, endpoints
AgentBase Container Registry (VCR) — lưu Docker image


System Architecture
┌─────────────────────────────────────────────────────┐
│           AgentBase Runtime (PUBLIC endpoint)        │
│                                                      │
│  ┌──────────┐     ┌──────────────────────────────┐  │
│  │  nginx   │────▶│       Streamlit App           │  │
│  │  :8080   │     │          :8501                │  │
│  │ /health  │     │  ┌────────────────────────┐  │  │
│  └──────────┘     │  │    agent/main.py        │  │  │
│                   │  │  - extract_risks()      │  │  │
│                   │  │  - check_compliance()   │  │  │
│                   │  │  - generate_email()     │  │  │
│                   │  └────────────┬───────────┘  │  │
│                   └───────────────┼──────────────┘  │
└───────────────────────────────────┼─────────────────┘
                                    │
                    ┌───────────────▼──────────────┐
                    │  GreenNode AI Platform (MaaS) │
                    │  - Gemma 4 31B (LLM)         │
                    │  - Whisper Large v3 (STT)    │
                    └──────────────────────────────┘

System Flow
1. Upload hợp đồng

User upload file PDF/DOCX/TXT → Streamlit đọc + parse text
2. Phân tích rủi ro

Text hợp đồng → extract_contract_risks() → gọi LLM với structured prompt → trả về JSON gồm: rủi ro pháp lý, tài chính, cảnh báo vàng, điểm đàm phán, cashflow table
3. Thẩm định đối tác

Tên công ty → check_compliance_mock() → LLM sinh báo cáo due diligence (PEPs, xung đột lợi ích, lịch sử)
4. Tạo email đàm phán

Risk points → generate_negotiation_email() → LLM soạn email tiếng Việt chuyên nghiệp
5. Q&A chat

User hỏi → run_agent() → LLM trả lời dựa trên context hợp đồng đã tải
