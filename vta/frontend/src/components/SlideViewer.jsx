import React, { useEffect, useRef, useState } from 'react';

/**
 * PDF slide viewer using PDF.js.
 * Navigates to specific pages on show_slide events.
 */
export default function SlideViewer({ pdfUrl, currentPage, onSlideLoaded }) {
  const canvasRef = useRef(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load PDF document
  useEffect(() => {
    console.log('[DEBUG SlideViewer] useEffect triggered, pdfUrl:', pdfUrl);
    if (!pdfUrl) {
      console.log('[DEBUG SlideViewer] No pdfUrl, returning early');
      return;
    }

    let cancelled = false;
    setLoading(true);
    console.log('[DEBUG SlideViewer] Starting PDF load from:', pdfUrl);

    (async () => {
      try {
        const pdfjsLib = await import('pdfjs-dist');

        // Use reliable CDN (unpkg) instead of cloudflare
        pdfjsLib.GlobalWorkerOptions.workerSrc =
          `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

        // Configure loading task with CORS support
        console.log('[DEBUG SlideViewer] Calling pdfjsLib.getDocument with url:', pdfUrl);
        const loadingTask = pdfjsLib.getDocument({
          url: pdfUrl,
          withCredentials: false,
          isEvalSupported: false,
        });

        console.log('[DEBUG SlideViewer] Waiting for PDF to load...');
        const doc = await loadingTask.promise;
        console.log('[DEBUG SlideViewer] PDF loaded successfully, pages:', doc.numPages);
        if (!cancelled) {
          setPdfDoc(doc);
          setLoading(false);
        }
      } catch (err) {
        console.error('[DEBUG SlideViewer] PDF load error:', err);
        if (!cancelled) {
          let errorMsg = `Failed to load PDF: ${err.message}`;
          if (err.message.includes('CORS') || err.message.includes('fetch')) {
            errorMsg += '\n\nThe PDF URL may not be publicly accessible. Please use a direct PDF link from a public source (e.g., Google Drive public link, Dropbox, or a CDN).';
          }
          console.log('[DEBUG SlideViewer] Setting error:', errorMsg);
          setError(errorMsg);
          setLoading(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [pdfUrl]);

  // Render specific page
  useEffect(() => {
    if (!pdfDoc || !currentPage || !canvasRef.current) return;

    let cancelled = false;

    (async () => {
      try {
        const page = await pdfDoc.getPage(currentPage);
        if (cancelled) return;

        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');

        // Scale to fit container
        const containerWidth = canvas.parentElement.clientWidth;
        const viewport = page.getViewport({ scale: 1 });
        const scale = containerWidth / viewport.width;
        const scaledViewport = page.getViewport({ scale });

        canvas.width = scaledViewport.width;
        canvas.height = scaledViewport.height;

        await page.render({
          canvasContext: context,
          viewport: scaledViewport,
        }).promise;

        if (!cancelled && onSlideLoaded) {
          onSlideLoaded(currentPage);
        }
      } catch (err) {
        console.error('Slide render error:', err);
      }
    })();

    return () => { cancelled = true; };
  }, [pdfDoc, currentPage, onSlideLoaded]);

  if (error) {
    return <div className="slide-viewer slide-error">{error}</div>;
  }

  if (loading) {
    return (
      <div className="slide-viewer slide-loading">
        Loading slides...
      </div>
    );
  }

  return (
    <div className="slide-viewer">
      <canvas ref={canvasRef} className="slide-canvas" />
      {pdfDoc && (
        <div className="slide-info">
          Slide {currentPage} of {pdfDoc.numPages}
        </div>
      )}
    </div>
  );
}
