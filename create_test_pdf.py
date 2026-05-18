#!/usr/bin/env python3
"""Crear PDF de prueba médico simple"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

pdf_path = Path("d:\Otros\Webs\HackIAthon\test_medical.pdf")

c = canvas.Canvas(str(pdf_path), pagesize=letter)
c.drawString(50, 750, "INFORME MÉDICO DE PRUEBA")
c.drawString(50, 720, "Paciente: Juan Carlos Pérez")
c.drawString(50, 690, "Cédula: 1234567890")
c.drawString(50, 660, "Edad: 45 años")
c.drawString(50, 630, "Diagnóstico: Hernia inguinal bilateral")
c.drawString(50, 600, "Tipo de Cirugía: Hernioplastía laparoscópica")
c.drawString(50, 570, "Médico Tratante: Dr. Roberto García")
c.drawString(50, 540, "Hospital: Clínica San José")
c.drawString(50, 510, "Fecha Solicitada: 2026-05-20")
c.drawString(50, 480, "Observaciones: Paciente apto para cirugía")
c.save()

print(f"✅ PDF creado: {pdf_path}")
