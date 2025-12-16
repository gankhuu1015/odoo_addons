import json
import datetime
from odoo.http import request
import werkzeug.wrappers
import base64
import os
import tempfile
import subprocess

def default(o):
    if isinstance(o, (datetime.datetime, datetime.date)):
        return o.isoformat()
    return str(o)

def valid_response(data, page=None, page_size=None, total=None, status=200):
    origin = request.httprequest.headers.get("Origin", "*")
    pagination = {}
    if page is not None and page_size is not None and total is not None:
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    response_data = {
        "success": True,
        "count": len(data) if isinstance(data, (list, dict)) else 1,
        "data": data,
    }

    if pagination:
        response_data.update(pagination)

    response = werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(response_data, default=default),
    )

    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return response

def invalid_response(message=None, status=401):
    origin = request.httprequest.headers.get("Origin", "*")
    response = werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps({
            "success": False,
            "message": str(message) or "Something went wrong",
        }, default=default),
    )
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return response


def extract_arguments(limit="80", offset=0, order="id", domain="", fields=[]):
    """Parse additional data  sent along request."""
    limit = int(limit)
    expresions = []
    if domain:
        expresions = [tuple(preg.replace(":", ",").split(",")) for preg in domain.split(",")]
        expresions = json.dumps(expresions)
        expresions = json.loads(expresions, parse_int=True)
    if fields:
        fields = fields.split(",")

    if offset:
        offset = int(offset)
    return [expresions, fields, offset, limit, order]


def convert_docx_to_pdf_and_keep_images(attachments, plan_number=None):
    attachments_data = []

    for att in attachments:
        pdf_base64 = None
        try:
            # ✅ DOCX → PDF convert
            if (
                att.mimetype
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                and att.datas
            ):
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_docx:
                    tmp_docx.write(base64.b64decode(att.datas))
                    tmp_docx.flush()
                    tmp_pdf_path = tmp_docx.name.replace(".docx", ".pdf")

                    subprocess.run([
                        "libreoffice",
                        "--headless",
                        "--convert-to", "pdf",
                        "--outdir", os.path.dirname(tmp_docx.name),
                        tmp_docx.name
                    ], check=True)

                    with open(tmp_pdf_path, "rb") as f_pdf:
                        pdf_base64 = base64.b64encode(f_pdf.read()).decode()

                    os.remove(tmp_docx.name)
                    os.remove(tmp_pdf_path)

            elif att.mimetype in ["image/jpeg", "image/jpg", "image/png"]:
                pdf_base64 = None  # not convert

            attachments_data.append({
                "id": att.id,
                "name": f"{plan_number or att.name}.pdf" if pdf_base64 else att.name,
                "mimetype": "application/pdf" if pdf_base64 else att.mimetype,
                "size": att.file_size,
                "create_name": getattr(att.create_uid, "name", "Unknown"),
                "create_date": att.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                "data": pdf_base64 or att.datas,
            })

        except Exception as e:
            attachments_data.append({
                "id": att.id,
                "name": att.name,
                "mimetype": att.mimetype,
                "error": str(e),
            })

    return attachments_data