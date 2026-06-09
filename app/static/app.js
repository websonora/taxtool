let currentDocumentId = null;
let currentFilename = null;
const selectedPages = new Set();

const priorPdf = document.getElementById('priorPdf');
const uploadPrior = document.getElementById('uploadPrior');
const priorStatus = document.getElementById('priorStatus');
const thumbnailGrid = document.getElementById('thumbnailGrid');
const createBackup = document.getElementById('createBackup');
const createStatus = document.getElementById('createStatus');
const taxYear = document.getElementById('taxYear');
const clientFilename = document.getElementById('clientFilename');
const newPdfs = document.getElementById('newPdfs');

function setStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle('error', isError);
}

function renderThumbnails(pageCount) {
  thumbnailGrid.innerHTML = '';
  selectedPages.clear();

  for (let page = 1; page <= pageCount; page += 1) {
    const button = document.createElement('button');
    button.className = 'thumb';
    button.type = 'button';
    button.dataset.page = String(page);

    const img = document.createElement('img');
    img.alt = `Page ${page}`;
    img.src = `/api/prior-pdf/${currentDocumentId}/thumbnail/${page}`;

    const label = document.createElement('span');
    label.textContent = `Page ${page}`;

    button.appendChild(img);
    button.appendChild(label);
    button.addEventListener('click', () => {
      if (selectedPages.has(page)) {
        selectedPages.delete(page);
        button.classList.remove('selected');
      } else {
        selectedPages.add(page);
        button.classList.add('selected');
      }
    });

    thumbnailGrid.appendChild(button);
  }
}

uploadPrior.addEventListener('click', async () => {
  if (!priorPdf.files.length) {
    setStatus(priorStatus, 'Select a prior-year PDF first.', true);
    return;
  }

  const form = new FormData();
  form.append('file', priorPdf.files[0]);
  setStatus(priorStatus, 'Uploading and reading PDF...');

  const response = await fetch('/api/prior-pdf', { method: 'POST', body: form });
  if (!response.ok) {
    setStatus(priorStatus, await response.text(), true);
    return;
  }

  const payload = await response.json();
  currentDocumentId = payload.document_id;
  currentFilename = payload.filename;
  if (!clientFilename.value) {
    clientFilename.value = currentFilename;
  }
  setStatus(priorStatus, `Opened ${payload.filename} with ${payload.page_count} pages.`);
  renderThumbnails(payload.page_count);
});

createBackup.addEventListener('click', async () => {
  if (!currentDocumentId) {
    setStatus(createStatus, 'Open a prior-year PDF first.', true);
    return;
  }
  if (!selectedPages.size) {
    setStatus(createStatus, 'Click at least one page to keep.', true);
    return;
  }

  const pages = Array.from(selectedPages).sort((a, b) => a - b);
  const form = new FormData();
  form.append('document_id', currentDocumentId);
  form.append('selected_pages', pages.join(','));
  form.append('tax_year', taxYear.value.trim());
  form.append('client_filename', clientFilename.value.trim() || currentFilename || 'client.pdf');
  for (const file of newPdfs.files) {
    form.append('current_year_files', file);
  }

  setStatus(createStatus, 'Creating backup PDF...');
  const response = await fetch('/api/create-backup', { method: 'POST', body: form });
  if (!response.ok) {
    setStatus(createStatus, await response.text(), true);
    return;
  }

  const payload = await response.json();
  setStatus(createStatus, `Created: ${payload.output_path}`);
});
