#!/bin/bash
# run_search_tests.sh - Script para ejecutar tests de búsqueda de productos

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Tests de Búsqueda de Productos${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar si pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest no encontrado!${NC}"
    echo -e "${YELLOW}Por favor instala las dependencias: pip install -r requirements.txt${NC}"
    exit 1
fi

MODE=${1:-"all"}

case $MODE in
    "api")
        echo -e "${GREEN}🔍 Ejecutando tests de API de búsqueda...${NC}"
        pytest inventory/tests.py::TestProductSearchAPI -v --tb=short
        ;;
    "form")
        echo -e "${GREEN}📝 Ejecutando tests del formulario de ventas...${NC}"
        pytest sales/tests.py::TestSaleFormView -v --tb=short
        pytest sales/tests.py::TestSaleFormProductSearch -v --tb=short
        ;;
    "integration")
        echo -e "${GREEN}🔗 Ejecutando tests de integración...${NC}"
        pytest sales/tests.py::TestSaleFormProductAddition -v --tb=short
        pytest sales/tests.py::TestSaleFormEdgeCases -v --tb=short
        ;;
    "critical")
        echo -e "${GREEN}🔥 Ejecutando tests CRÍTICOS de búsqueda...${NC}"
        pytest inventory/tests.py::TestProductSearchAPI -v --tb=short -m critical
        pytest sales/tests.py -v --tb=short -m critical -k "search or form"
        ;;
    "all")
        echo -e "${GREEN}🎯 Ejecutando TODOS los tests de búsqueda...${NC}"
        echo ""
        echo -e "${BLUE}--- 1. Tests de API de Búsqueda ---${NC}"
        pytest inventory/tests.py::TestProductSearchAPI -v --tb=short
        echo ""
        echo -e "${BLUE}--- 2. Tests del Formulario ---${NC}"
        pytest sales/tests.py::TestSaleFormView -v --tb=short
        pytest sales/tests.py::TestSaleFormProductSearch -v --tb=short
        echo ""
        echo -e "${BLUE}--- 3. Tests de Integración ---${NC}"
        pytest sales/tests.py::TestSaleFormProductAddition -v --tb=short
        pytest sales/tests.py::TestSaleFormEdgeCases -v --tb=short
        ;;
    "coverage")
        echo -e "${GREEN}📊 Ejecutando tests con cobertura...${NC}"
        pytest \
            inventory/tests.py::TestProductSearchAPI \
            sales/tests.py::TestSaleFormView \
            sales/tests.py::TestSaleFormProductSearch \
            sales/tests.py::TestSaleFormProductAddition \
            sales/tests.py::TestSaleFormEdgeCases \
            --cov=inventory.api_views \
            --cov=sales \
            --cov-report=html \
            --cov-report=term-missing \
            -v
        echo ""
        echo -e "${BLUE}📊 Reporte de cobertura: htmlcov/index.html${NC}"
        ;;
    "help")
        echo "Uso: ./run_search_tests.sh [modo]"
        echo ""
        echo "Modos:"
        echo "  api          Ejecutar solo tests de API de búsqueda"
        echo "  form         Ejecutar solo tests del formulario"
        echo "  integration  Ejecutar solo tests de integración"
        echo "  critical     Ejecutar solo tests críticos"
        echo "  all          Ejecutar todos los tests de búsqueda (default)"
        echo "  coverage     Ejecutar con reporte de cobertura"
        echo "  help         Mostrar esta ayuda"
        echo ""
        echo "Ejemplos:"
        echo "  ./run_search_tests.sh api"
        echo "  ./run_search_tests.sh critical"
        echo "  ./run_search_tests.sh coverage"
        ;;
    *)
        echo -e "${RED}❌ Modo desconocido: $MODE${NC}"
        echo -e "${YELLOW}Ejecuta ./run_search_tests.sh help para ver opciones${NC}"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
echo -e "${BLUE}========================================${NC}"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Tests completados exitosamente!${NC}"
else
    echo -e "${RED}❌ Algunos tests fallaron${NC}"
fi
echo -e "${BLUE}========================================${NC}"

exit $EXIT_CODE
