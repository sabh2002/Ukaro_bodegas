# finances/pdf_generators.py
# Generadores de PDF para reportes usando ReportLab

from datetime import date, datetime
from io import BytesIO

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


# Paleta de colores
DARK_BLUE = colors.HexColor('#1e3a5f')
LIGHT_BLUE = colors.HexColor('#2563eb')
HEADER_BG = colors.HexColor('#1e40af')
ROW_ALT = colors.HexColor('#f0f4ff')
GRAY_LIGHT = colors.HexColor('#f9fafb')
TEXT_DARK = colors.HexColor('#111827')
TEXT_GRAY = colors.HexColor('#6b7280')
GREEN = colors.HexColor('#16a34a')
RED = colors.HexColor('#dc2626')
ORANGE = colors.HexColor('#ea580c')


def generate_pdf_response(title, headers, rows, summary=None, metadata=None,
                          landscape_mode=False, filename='reporte.pdf'):
    """
    Genera una HttpResponse con PDF usando ReportLab.

    Args:
        title: Título del reporte
        headers: Lista de strings para cabeceras de columnas
        rows: Lista de listas con los datos de cada fila
        summary: Lista de tuplas (etiqueta, valor) para la tabla de totales
        metadata: Lista de tuplas (etiqueta, valor) para mostrar en el header del reporte
        landscape_mode: Si True usa orientación horizontal
        filename: Nombre del archivo a descargar
    """
    buffer = BytesIO()
    pagesize = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # --- Título ---
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        textColor=DARK_BLUE,
        fontSize=18,
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    story.append(Paragraph(title, title_style))

    # --- Metadata ---
    if metadata:
        meta_data_rows = []
        for i in range(0, len(metadata), 2):
            row = []
            label1, val1 = metadata[i]
            row.append(Paragraph(f'<b>{label1}:</b> {val1}', styles['Normal']))
            if i + 1 < len(metadata):
                label2, val2 = metadata[i + 1]
                row.append(Paragraph(f'<b>{label2}:</b> {val2}', styles['Normal']))
            else:
                row.append(Paragraph('', styles['Normal']))
            meta_data_rows.append(row)

        meta_table = Table(meta_data_rows, colWidths=['50%', '50%'])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.3 * cm))

    # Fecha de generación
    gen_line = ParagraphStyle(
        'GenLine', parent=styles['Normal'], textColor=TEXT_GRAY, fontSize=7
    )
    story.append(Paragraph(
        f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        gen_line
    ))
    story.append(Spacer(1, 0.5 * cm))

    # --- Tabla principal ---
    if rows:
        # Calcular anchos de columna distribuyendo el espacio disponible
        usable_width = (landscape(A4)[0] if landscape_mode else A4[0]) - 3 * cm
        col_count = len(headers)
        col_width = usable_width / col_count

        table_data = [headers] + rows
        main_table = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)

        table_style_cmds = [
            # Cabecera
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            # Filas
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ]
        main_table.setStyle(TableStyle(table_style_cmds))
        story.append(main_table)
    else:
        story.append(Paragraph('No hay datos para mostrar en este período.', styles['Normal']))

    # --- Resumen / Totales ---
    if summary:
        story.append(Spacer(1, 0.6 * cm))
        story.append(HRFlowable(width='100%', thickness=1, color=DARK_BLUE))
        story.append(Spacer(1, 0.3 * cm))

        summary_label_style = ParagraphStyle(
            'SummaryLabel', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9, textColor=DARK_BLUE
        )
        story.append(Paragraph('Resumen', summary_label_style))
        story.append(Spacer(1, 0.2 * cm))

        summary_rows = [[Paragraph(f'<b>{lbl}</b>', styles['Normal']),
                         Paragraph(str(val), styles['Normal'])]
                        for lbl, val in summary]
        summary_table = Table(summary_rows, colWidths=['50%', '50%'])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, DARK_BLUE),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, GRAY_LIGHT]),
        ]))
        story.append(summary_table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response


# ============================================================================
# FUNCIONES ESPECÍFICAS POR REPORTE
# ============================================================================

def pdf_sales_report(sales_qs, totals, metadata=None):
    """PDF para reporte de ventas"""
    headers = ['#Venta', 'Fecha', 'Cliente', 'Empleado', 'Método', 'Total USD', 'Total Bs']

    rows = []
    for sale in sales_qs:
        customer = sale.customer.name if sale.customer else 'Cliente General'
        employee = sale.user.get_full_name() or sale.user.username if sale.user else '-'
        if sale.is_credit:
            method = 'Crédito'
        else:
            method = sale.get_payment_method_display()
        rows.append([
            f'#{sale.id}',
            sale.date.strftime('%d/%m/%Y %H:%M'),
            customer,
            employee,
            method,
            f'${float(sale.total_usd):.2f}',
            f'Bs {float(sale.total_bs):.2f}',
        ])

    summary = [
        ('Total USD', f'${float(totals.get("total_usd") or 0):.2f}'),
        ('Total Bs', f'Bs {float(totals.get("total_bs") or 0):.2f}'),
        ('Cantidad de Ventas', str(totals.get('count') or 0)),
    ]

    return generate_pdf_response(
        title='Reporte de Ventas',
        headers=headers,
        rows=rows,
        summary=summary,
        metadata=metadata,
        landscape_mode=True,
        filename=f'reporte_ventas_{date.today().strftime("%Y%m%d")}.pdf',
    )


def pdf_purchases_report(orders_qs, totals, metadata=None):
    """PDF para reporte de compras"""
    headers = ['#Orden', 'Fecha', 'Proveedor', 'Total USD', 'Total Bs', 'Estado Pago']

    rows = []
    for order in orders_qs:
        rows.append([
            f'#{order.id}',
            order.order_date.strftime('%d/%m/%Y %H:%M'),
            order.supplier.name,
            f'${float(order.total_usd):.2f}',
            f'Bs {float(order.total_bs):.2f}',
            order.payment_status_display,
        ])

    summary = [
        ('Total USD', f'${float(totals.get("total_usd") or 0):.2f}'),
        ('Total Bs', f'Bs {float(totals.get("total_bs") or 0):.2f}'),
        ('Cantidad de Órdenes', str(totals.get('count') or 0)),
    ]

    return generate_pdf_response(
        title='Reporte de Compras',
        headers=headers,
        rows=rows,
        summary=summary,
        metadata=metadata,
        landscape_mode=True,
        filename=f'reporte_compras_{date.today().strftime("%Y%m%d")}.pdf',
    )


def pdf_inventory_report(products_list, totals, metadata=None):
    """PDF para reporte de inventario"""
    headers = ['Producto', 'Código', 'Categoría', 'Stock', 'Mín', 'P.Compra USD', 'P.Venta USD', 'Valor USD']

    rows = []
    for p in products_list:
        value = float(p.stock) * float(p.purchase_price_usd)
        rows.append([
            p.name[:30],
            p.barcode or '-',
            p.category.name if p.category else '-',
            str(float(p.stock)),
            str(float(p.min_stock)),
            f'${float(p.purchase_price_usd):.2f}',
            f'${float(p.selling_price_usd):.2f}',
            f'${value:.2f}',
        ])

    summary = [
        ('Total Productos', str(totals.get('count', 0))),
        ('Valor Total USD', f'${float(totals.get("total_value_usd", 0)):.2f}'),
        ('Productos Bajo Stock', str(totals.get('low_stock_count', 0))),
        ('Sin Stock', str(totals.get('out_of_stock_count', 0))),
    ]

    return generate_pdf_response(
        title='Reporte de Inventario',
        headers=headers,
        rows=rows,
        summary=summary,
        metadata=metadata,
        landscape_mode=True,
        filename=f'reporte_inventario_{date.today().strftime("%Y%m%d")}.pdf',
    )


def pdf_credits_report(credits_data, aging, metadata=None):
    """PDF para reporte de cuentas por cobrar"""
    headers = ['#', 'Cliente', 'Venta #', 'Monto USD', 'Pagado', 'Saldo', 'Vencimiento', 'Días Mora']

    rows = []
    for i, c in enumerate(credits_data, 1):
        rows.append([
            str(i),
            c['customer'][:25],
            f'#{c["sale_id"]}',
            f'${c["amount"]:.2f}',
            f'${c["paid"]:.2f}',
            f'${c["balance"]:.2f}',
            c['date_due'].strftime('%d/%m/%Y') if c['date_due'] else '-',
            str(c['days_overdue']) if c['days_overdue'] > 0 else '-',
        ])

    total_balance = sum(c['balance'] for c in credits_data)
    total_amount = sum(c['amount'] for c in credits_data)

    summary = [
        ('Total Créditos', str(len(credits_data))),
        ('Monto Total USD', f'${total_amount:.2f}'),
        ('Saldo Pendiente USD', f'${total_balance:.2f}'),
        ('Vigente', f'${aging["current"]:.2f}'),
        ('1-30 días', f'${aging["days_1_30"]:.2f}'),
        ('31-60 días', f'${aging["days_31_60"]:.2f}'),
        ('+60 días', f'${aging["over_60"]:.2f}'),
    ]

    return generate_pdf_response(
        title='Reporte de Cuentas por Cobrar',
        headers=headers,
        rows=rows,
        summary=summary,
        metadata=metadata,
        landscape_mode=True,
        filename=f'reporte_creditos_{date.today().strftime("%Y%m%d")}.pdf',
    )


def pdf_supplier_debt_report(suppliers_data, total_debt, metadata=None):
    """PDF para reporte de deuda a proveedores"""
    headers = ['Proveedor', 'Teléfono', '# Órdenes', 'Total Comprado USD', 'Pagado USD', 'Deuda USD']

    rows = []
    for s in suppliers_data.values():
        rows.append([
            s['name'][:30],
            s['phone'] or '-',
            str(s['order_count']),
            f'${s["total_usd"]:.2f}',
            f'${s["paid_usd"]:.2f}',
            f'${s["debt_usd"]:.2f}',
        ])

    summary = [
        ('Total Proveedores con Deuda', str(len(suppliers_data))),
        ('Deuda Total USD', f'${total_debt:.2f}'),
    ]

    return generate_pdf_response(
        title='Reporte de Deuda a Proveedores',
        headers=headers,
        rows=rows,
        summary=summary,
        metadata=metadata,
        landscape_mode=False,
        filename=f'reporte_deuda_proveedores_{date.today().strftime("%Y%m%d")}.pdf',
    )
