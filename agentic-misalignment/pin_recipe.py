from inspect_ai.log import read_eval_log
import glob

for f in sorted(glob.glob(r'logs\*.eval')):
    log = read_eval_log(f)
    if 'gemma-3-12b' in (log.eval.model or ''):
        ta = log.eval.task_args or {}
        print(f, '\n', log.eval.model)
        print('task_args:', ta)
        print('--- full eval block (find temperature/sampling here) ---')
        print(log.eval.model_dump_json(indent=2))
        # exact scenario prompt actually sent:
        print('--- system prompt of sample 0 ---')
        print(log.samples[0].messages[0].content[:2000])
        break