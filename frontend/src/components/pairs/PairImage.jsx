/**
 * PairImage.jsx -- one face image fetched through the secured /api/image
 * endpoint, with a graceful fallback when the image cannot be served
 * (missing file, path outside the image directory, or Flask down). A broken
 * image icon is never shown; the tile explains itself instead.
 */

import { useEffect, useState } from "react";

export default function PairImage({ path, alt, label }) {
  const [hasError, setHasError] = useState(false);

  // Reset the error state when a different path is rendered.
  useEffect(() => {
    setHasError(false);
  }, [path]);

  // Show only the filename, whatever separators the report used.
  const fileName = path ? path.split(/[\\/]/).pop() : "";

  return (
    <figure className="flex flex-col items-center gap-2">
      {hasError || !path ? (
        <div className="flex h-56 w-56 items-center justify-center rounded border border-dashed border-slate-300 bg-slate-50 p-4 text-center text-xs text-slate-500">
          {path
            ? "Image unavailable — missing file or outside the configured image directory."
            : "No image path recorded for this pair."}
        </div>
      ) : (
        <img
          src={`/api/image?path=${encodeURIComponent(path)}`}
          alt={alt}
          onError={() => setHasError(true)}
          className="h-56 w-56 rounded border border-slate-200 bg-slate-50 object-cover"
        />
      )}
      <figcaption className="text-center text-xs text-slate-500">
        <span className="font-medium text-slate-700">{label}</span>
        {fileName && <> · {fileName}</>}
      </figcaption>
    </figure>
  );
}
