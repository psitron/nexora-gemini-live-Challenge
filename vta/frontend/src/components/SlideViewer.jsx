import React, { useEffect, useRef, useState } from 'react';

/**
 * Slide viewer — shows PDF pages or text-based slides.
 * Falls back to text slides when no PDF is available.
 */
export default function SlideViewer({ pdfUrl, currentPage, currentTask, onSlideLoaded }) {
  const canvasRef = useRef(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load PDF document (if URL provided)
  useEffect(() => {
    if (!pdfUrl) return;

    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        const pdfjsLib = await import('pdfjs-dist');
        pdfjsLib.GlobalWorkerOptions.workerSrc =
          `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

        const loadingTask = pdfjsLib.getDocument({
          url: pdfUrl,
          withCredentials: false,
          isEvalSupported: false,
        });

        const doc = await loadingTask.promise;
        if (!cancelled) {
          setPdfDoc(doc);
          setLoading(false);
        }
      } catch (err) {
        console.error('PDF load error:', err);
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [pdfUrl]);

  // Render PDF page
  useEffect(() => {
    if (!pdfDoc || !currentPage || !canvasRef.current) return;

    let cancelled = false;

    (async () => {
      try {
        const page = await pdfDoc.getPage(currentPage);
        if (cancelled) return;

        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
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

  // If PDF loaded successfully, show it
  if (pdfDoc) {
    return (
      <div className="slide-viewer">
        <canvas ref={canvasRef} className="slide-canvas" />
        <div className="slide-info">
          Slide {currentPage} of {pdfDoc.numPages}
        </div>
      </div>
    );
  }

  // No PDF — show text-based slide card
  if (currentTask) {
    return (
      <div className="slide-viewer">
        <div className="text-slide">
          <div className="text-slide-header">
            <span className="text-slide-number">Slide {currentPage}</span>
            <span className="text-slide-type">{currentTask.type || 'theory'}</span>
          </div>
          <h2 className="text-slide-title">{currentTask.title || 'Untitled'}</h2>
          <div className="text-slide-content">
            {currentTask.slide_context || currentTask.sonic_prompt || 'Listen to ARIA for this section.'}
          </div>
          {currentTask.goal && (
            <div className="text-slide-goal">
              <strong>Goal:</strong> {currentTask.goal}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="slide-viewer slide-loading">Loading slides...</div>;
  }

  // Default — waiting for tutorial to start
  return (
    <div className="slide-viewer">
      <div className="text-slide">
        <h2 className="text-slide-title">Welcome</h2>
        <div className="text-slide-content">
          Start the tutorial to begin learning.
        </div>
      </div>
    </div>
  );
}
