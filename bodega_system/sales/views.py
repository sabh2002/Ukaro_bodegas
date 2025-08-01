# sales/views.py

import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.template.loader import get_template
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from .models import Sale, SaleItem
from utils.models import ExchangeRate

@login_required
def sale_list(request):
    """Vista para listar ventas"""
    # Obtener ventas ordenadas por fecha (más recientes primero)
    sales = Sale.objects.all().order_by('-date')
    
    return render(request, 'sales/sale_list.html', {
        'sales': sales
    })

@login_required
def sale_create(request):
    """Vista para crear una nueva venta"""
    # Esta vista simplemente muestra el formulario, el procesamiento se hace vía API
    return render(request, 'sales/sale_form.html', {
        'title': 'Nueva Venta'
    })

@login_required
def sale_detail(request, pk):
    """Vista para ver detalles de una venta"""
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.all()
    
    return render(request, 'sales/sale_detail.html', {
        'sale': sale,
        'items': items
    })

@login_required
def sale_receipt(request, pk):
    """Vista para generar recibo PDF de una venta"""
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.all()
    
    # Obtener tasa de cambio actual
    exchange_rate = ExchangeRate.get_latest_rate()
    
    # Crear un buffer para el PDF
    buffer = io.BytesIO()
    
    # Crear el PDF
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Estilos para el PDF
    styles = getSampleStyleSheet()
    
    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width/2, height - 1*inch, "Sistema de Bodega")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height - 1.3*inch, f"Recibo de Venta #{sale.id}")
    
    # Información de la venta
    p.setFont("Helvetica", 10)
    p.drawString(1*inch, height - 2*inch, f"Fecha: {sale.date.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(1*inch, height - 2.2*inch, f"Atendido por: {sale.user.get_full_name() or sale.user.username}")
    
    if sale.customer:
        p.drawString(1*inch, height - 2.4*inch, f"Cliente: {sale.customer.name}")
        if sale.is_credit:
            p.drawString(1*inch, height - 2.6*inch, "Tipo: CRÉDITO")
    else:
        p.drawString(1*inch, height - 2.4*inch, "Cliente: Consumidor Final")
    
    # Tabla de productos
    data = [["Producto", "Cantidad", "Precio Unit.", "Subtotal"]]
    
    for item in items:
        data.append([
            item.product.name, 
            str(item.quantity), 
            f"Bs {item.price_bs:.2f}", 
            f"Bs {item.subtotal:.2f}"
        ])
    
    table = Table(data, colWidths=[3*inch, 1*inch, 1.2*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Dibujar la tabla
    table.wrapOn(p, width, height)
    table.drawOn(p, 0.6*inch, height - 4*inch - len(data)*0.25*inch)
    
    # Total
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(6.4*inch, height - 4.5*inch - len(data)*0.25*inch, f"Total: Bs {sale.total_bs:.2f}")
    
    if exchange_rate:
        p.setFont("Helvetica", 10)
        usd_total = sale.total_bs / exchange_rate.bs_to_usd
        p.drawRightString(6.4*inch, height - 4.8*inch - len(data)*0.25*inch, f"Equivalente: $ {usd_total:.2f}")
    
    # Pie de página
    p.setFont("Helvetica", 8)
    p.drawCentredString(width/2, 0.5*inch, "Gracias por su compra")
    
    # Finalizar PDF
    p.showPage()
    p.save()
    
    # Configurar la respuesta
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=recibo_venta_{sale.id}.pdf'
    
    return response