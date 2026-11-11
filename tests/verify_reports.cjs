'use strict';

// Comprueba la interfaz real sin ejecutar cadenas de código.
const assert = require('node:assert/strict');

async function main() {
  const elements = new Map();

  function element(selector) {
    if (!elements.has(selector)) {
      elements.set(selector, {
        innerHTML: '',
        textContent: '',
        value: selector === '#cut' ? '2026-11-09' : '',
        hidden: false,
        classList: {
          toggle() {}
        },
        addEventListener() {},
        setAttribute() {},
        insertBefore() {},
        querySelectorAll: () => []
      });
    }

    return elements.get(selector);
  }

  const reportsButton = {
    dataset: {
      page: 'reports'
    },
    classList: {
      toggle() {}
    }
  };

  const fixture = {
    user: {
      id: 1,
      username: 'profesor',
      role: 'bibliotecario'
    },
    books: [],
    users: [],
    reservations: [],
    notices: [],
    audit: [],
    loans: [
      {
        id: 1,
        code: 'E001',
        borrower: 'franco',
        start: '2026-11-01',
        due: '2026-11-06',
        returned: '2026-11-09',
        fine: 4500
      },
      {
        id: 2,
        code: 'E002',
        borrower: 'ana',
        start: '2026-11-01',
        due: '2026-11-08',
        returned: null,
        fine: 0
      },
      {
        id: 3,
        code: 'E003',
        borrower: 'franco',
        start: '2026-11-01',
        due: '2026-11-07',
        returned: '2026-11-09',
        fine: 3000
      }
    ]
  };

  const originalFixture = JSON.stringify(fixture);

  // Simula únicamente los elementos que necesita la interfaz.
  const replacements = {
    document: {
      querySelector: element,

      querySelectorAll: selector =>
        selector === '[data-page]' ? [reportsButton] : [],

      createElement: () => ({
        className: '',
        innerHTML: '',
        setAttribute() {},
        querySelectorAll: () => []
      })
    },

    sessionStorage: {
      getItem: () => '',
      setItem() {},
      removeItem() {}
    },

    fetch: async path => {
      assert.equal(path, '/api/state');

      return {
        ok: true,
        json: async () => fixture
      };
    }
  };

  const originals = new Map();

  for (const [name, value] of Object.entries(replacements)) {
    originals.set(
      name,
      Object.getOwnPropertyDescriptor(globalThis, name)
    );

    Object.defineProperty(globalThis, name, {
      value,
      configurable: true,
      writable: true
    });
  }

  try {
    // Carga normal del archivo utilizado por el navegador.
    require('../static/app.js');

    // Espera a que termine la carga inicial de los datos simulados.
    await new Promise(resolve => setImmediate(resolve));

    assert.equal(
      element('#workspace').hidden,
      false,
      'Debe cargar el estado inicial'
    );

    assert.match(
      element('#content').innerHTML,
      /Reservas pendientes/
    );

    // Abre Reportes mediante el evento real de navegación.
    reportsButton.onclick();

    // Comprueba el corte del 9 de noviembre.
    let output = element('#reportBody').innerHTML;

    assert(output.includes('$7.500'));

    let tables = output.match(/<table>.*?<\/table>/g);

    assert(tables && tables.length === 3);
    assert(tables[0].includes('E002'));
    assert(!tables[0].includes('E001'));
    assert(tables[1].includes('4.500'));
    assert(tables[1].includes('3.000'));

    // Comprueba el corte histórico del 8 de noviembre.
    element('#cut').value = '2026-11-08';
    element('#cut').onchange();

    output = element('#reportBody').innerHTML;
    tables = output.match(/<table>.*?<\/table>/g);

    assert(tables && tables.length === 3);
    assert(tables[0].includes('E001'));
    assert(tables[0].includes('E003'));
    assert(!tables[0].includes('E002'));
    assert(tables[1].includes('Sin registros'));
    assert(!output.includes('$7.500'));

    // Los reportes deben conservar los datos originales.
    assert.equal(
      JSON.stringify(fixture),
      originalFixture,
      'Los reportes no deben modificar los datos'
    );

    console.log(
      'OK: dos salidas de reporte, corte actual e histórico, importes y registros originales.'
    );
  } finally {
    // Restaura las variables globales después de la prueba.
    for (const [name, descriptor] of originals) {
      if (descriptor) {
        Object.defineProperty(globalThis, name, descriptor);
      } else {
        Reflect.deleteProperty(globalThis, name);
      }
    }
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});