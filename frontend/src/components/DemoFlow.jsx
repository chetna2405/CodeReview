import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Check, AlertCircle, RefreshCw, Share2 } from 'lucide-react';
import { api } from '@/lib/api';
import { useSettings } from '../App';
import { cn } from '@/lib/utils';

const STEPS = [
  'Setup',
  'Execute',
  'Grade',
  'Analyze',
  'Complete'
];

const waitForElement = (selector, timeout = 3000) =>
  new Promise((resolve, reject) => {
    const el = document.querySelector(selector);
    if (el) return resolve(el);
    const observer = new MutationObserver(() => {
      const el = document.querySelector(selector);
      if (el) {
        observer.disconnect();
        resolve(el);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => {
      observer.disconnect();
      reject(new Error(`Timeout waiting for element: ${selector}`));
    }, timeout);
  });

export default function DemoFlow() {
  const navigate = useNavigate();
  const { setSettings } = useSettings();
  const [demoState, setDemoState] = useState('idle'); // idle, running, complete, error
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');
  const [errorDetails, setErrorDetails] = useState(null);
  const [episodeId, setEpisodeId] = useState(null);

  // Expose reset for retry
  const startDemo = async (startFromIndex = 0) => {
    setDemoState('running');
    setErrorMsg('');
    setErrorDetails(null);
    if (startFromIndex === 0) setEpisodeId(null);
    setCurrentStepIndex(startFromIndex);

    let activeEpisodeId = startFromIndex === 0 ? null : episodeId;

    try {
      // -- STEP 1: Setup
      if (startFromIndex <= 0) {
        setCurrentStepIndex(0);
        navigate('/new-review');
        await new Promise(r => setTimeout(r, 600));

        // Highlight card
        const card = await waitForElement('[data-demo-target="simple_review"]');
        card.classList.add('ring-4', 'ring-accent', 'animate-pulse');
        await new Promise(r => setTimeout(r, 800));

        // Reset episode
        const res = await api.resetEpisode({ task_id: 'simple_review', seed: 42 });
        activeEpisodeId = res.metadata.episode_id;
        setEpisodeId(activeEpisodeId);
        setSettings(s => ({ ...s, episodeId: activeEpisodeId }));
        await new Promise(r => setTimeout(r, 600));
        card.classList.remove('ring-4', 'ring-accent', 'animate-pulse');
      }

      // -- STEP 2: Execute
      if (startFromIndex <= 1) {
        setCurrentStepIndex(1);
        navigate('/review');
        await new Promise(r => setTimeout(r, 600));

        // Dynamically get context lines
        const ctx = await api.getContext({ episode_id: activeEpisodeId, task_id: 'simple_review' });
        const lines = ctx.content.split('\n');
        
        const realChangedLines = [];
        lines.forEach((l, i) => {
          if (l.startsWith('+') || l.startsWith('-')) realChangedLines.push(i + 1); // 1-indexed approx
        });

        const line1 = realChangedLines[0] || 5;
        const line2 = realChangedLines[2] || realChangedLines[1] || 12;

        await api.step({
          episode_id: activeEpisodeId,
          action_type: 'add_comment',
          line_number: line1,
          severity: 'critical',
          message: 'Null pointer dereference: user input unchecked'
        });
        await new Promise(r => setTimeout(r, 600));

        await api.step({
          episode_id: activeEpisodeId,
          action_type: 'add_comment',
          line_number: line2,
          severity: 'major',
          message: 'Missing input validation on email field'
        });
        await new Promise(r => setTimeout(r, 600));

        await api.step({
          episode_id: activeEpisodeId,
          action_type: 'finalize_review'
        });
        await new Promise(r => setTimeout(r, 800));
      }

      // -- STEP 3: Grade
      if (startFromIndex <= 2) {
        setCurrentStepIndex(2);
        navigate(`/grader?episode_id=${activeEpisodeId}`);
        await new Promise(r => setTimeout(r, 2000));
      }

      // -- STEP 4: Analyze
      if (startFromIndex <= 3) {
        setCurrentStepIndex(3);
        navigate('/metrics');
        await new Promise(r => setTimeout(r, 800));
        await api.runBaseline({ model: 'rule-based', seed: 42 });
        await new Promise(r => setTimeout(r, 2000));
      }

      // -- STEP 5: Complete
      if (startFromIndex <= 4) {
        setCurrentStepIndex(4);
        navigate('/');
        setDemoState('complete');
      }

    } catch (err) {
      console.error(err);
      setDemoState('error');
      setErrorMsg(err.message || 'Unknown error occurred');
      setErrorDetails(err.toString());
    }
  };

  const handleShare = () => {
    if (!episodeId) return;
    const url = `${window.location.origin}/?demo=replay&episode_id=${episodeId}`;
    navigator.clipboard.writeText(url);
    alert('Shareable URL copied to clipboard!');
  };

  if (demoState === 'idle') {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => startDemo(0)}
          className="flex items-center gap-2 bg-success text-[#050507] px-5 py-3 rounded-full font-bold shadow-[0_0_20px_rgba(110,231,183,0.4)] hover:shadow-[0_0_30px_rgba(110,231,183,0.6)] transition-shadow"
        >
          <Play className="w-5 h-5 fill-current" />
          Run Demo
        </motion.button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[400px]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="surface-card p-5 border-success/30 shadow-2xl"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-text-primary text-[14px]">Demo Progress</h3>
          {demoState === 'complete' && (
            <span className="text-[12px] font-medium text-success bg-success/10 px-2 py-0.5 rounded">
              CodeReviewEnv validated ✅
            </span>
          )}
        </div>

        <div className="space-y-3 mb-4">
          {STEPS.map((step, idx) => (
            <div key={step} className="flex items-center gap-3">
              <div className={cn(
                "w-5 h-5 rounded-full flex items-center justify-center shrink-0 border",
                currentStepIndex > idx || demoState === 'complete' 
                  ? "bg-success border-success text-[#050507]"
                  : currentStepIndex === idx && demoState === 'running'
                  ? "border-success text-success bg-transparent animate-pulse"
                  : currentStepIndex === idx && demoState === 'error'
                  ? "bg-danger border-danger text-white"
                  : "border-text-dim text-text-dim"
              )}>
                {(currentStepIndex > idx || demoState === 'complete') ? (
                  <Check className="w-3 h-3 stroke-[3]" />
                ) : (
                  <span className="text-[10px] font-bold">{idx + 1}</span>
                )}
              </div>
              <span className={cn(
                "text-[13px] font-medium transition-colors",
                (currentStepIndex >= idx || demoState === 'complete') ? "text-text-primary" : "text-text-dim",
                currentStepIndex === idx && demoState === 'error' && "text-danger"
              )}>
                {step}
              </span>
            </div>
          ))}
        </div>

        {demoState === 'error' && (
          <div className="bg-danger/10 border border-danger/20 rounded-lg p-3 mb-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-danger shrink-0 mt-0.5" />
              <div>
                <p className="text-[13px] font-medium text-danger">{errorMsg}</p>
                <details className="mt-2 text-[11px] text-text-muted cursor-pointer">
                  <summary className="font-medium outline-none">Debug Payload</summary>
                  <pre className="mt-2 p-2 bg-[#050507] rounded border border-subtle overflow-x-auto">
                    {errorDetails}
                  </pre>
                </details>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-subtle">
          {demoState === 'running' && (
            <p className="text-[12px] text-text-muted flex-1">Auto-navigating application...</p>
          )}
          {demoState === 'error' && (
            <>
              <button 
                onClick={() => setDemoState('idle')}
                className="text-[12px] text-text-secondary hover:text-text-primary mr-auto"
              >
                Cancel
              </button>
              <button 
                onClick={() => startDemo(currentStepIndex)}
                className="btn-primary py-1.5 px-3 text-[12px] flex items-center gap-1.5"
              >
                <RefreshCw className="w-3 h-3" /> Retry Step
              </button>
            </>
          )}
          {demoState === 'complete' && (
            <>
              <button 
                onClick={() => setDemoState('idle')}
                className="text-[12px] text-text-secondary hover:text-text-primary mr-auto"
              >
                Close
              </button>
              <button 
                onClick={handleShare}
                className="btn-primary py-1.5 px-3 text-[12px] flex items-center gap-1.5 bg-accent text-white"
              >
                <Share2 className="w-3 h-3" /> Share Results
              </button>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
