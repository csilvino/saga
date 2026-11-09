import { useState, useCallback, useRef, useEffect } from 'react';

export const useHistory = (initialState) => {
  const [state, setState] = useState({
    history: [initialState],
    index: 0
  });

  const set = useCallback((newState, overwrite = false) => {
    setState(prevState => {
      if (overwrite) {
        return { history: [newState], index: 0 };
      }
      const newHistory = prevState.history.slice(0, prevState.index + 1);
      newHistory.push(newState);
      return { history: newHistory, index: newHistory.length - 1 };
    });
  }, []);

  const undo = useCallback(() => {
    setState(prevState => ({
      ...prevState,
      index: prevState.index > 0 ? prevState.index - 1 : 0
    }));
  }, []);

  const redo = useCallback(() => {
    setState(prevState => ({
      ...prevState,
      index: prevState.index < prevState.history.length - 1 ? prevState.index + 1 : prevState.index
    }));
  }, []);

  return [state.history[state.index], set, undo, redo];
};

export const useResizable = (initialWidth, minWidth = 200, maxWidth = 600) => {
  const [width, setWidth] = useState(initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(initialWidth);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = width;
  }, [width]);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - startXRef.current;
      const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidthRef.current + delta));
      setWidth(newWidth);
    };

    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, minWidth, maxWidth]);

  return { width, isResizing, handleMouseDown };
};

export const useRightResizable = (initialWidth, minWidth = 200, maxWidth = 600) => {
  const [width, setWidth] = useState(initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(initialWidth);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = width;
  }, [width]);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = startXRef.current - e.clientX; // Lógica correta para o painel direito
      const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidthRef.current + delta));
      setWidth(newWidth);
    };

    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, minWidth, maxWidth]);

  return { width, isResizing, handleMouseDown };
};
