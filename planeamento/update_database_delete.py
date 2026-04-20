from pathlib import Path

path = Path('database.py')
text = path.read_text()

old = "    def delete_planning_assignment(\r\n        self,\r\n        assignment_date: date,\r\n        team_code: str,\r\n        project_code: str,\r\n    ) -> None:\r\n        \"\"\"Remove a planning assignment row from u_plano.\"\"\"\r\n        query = (\r\n            \"DELETE FROM u_plano WHERE data = ? AND fref = ? AND processo = ?\"\r\n        )\r\n        params = (assignment_date, team_code, project_code)\r\n        try:\r\n            with self.connect() as conn:\r\n                cursor = conn.cursor()\r\n                cursor.execute(query, params)\r\n                conn.commit()\r\n        except Exception as exc:\r\n            raise RuntimeError(str(exc)) from exc\r\n"

new = "    def delete_planning_assignment(\r\n        self,\r\n        assignment_date: date,\r\n        team_code: str,\r\n        project_code: str,\r\n    ) -> None:\r\n        \"\"\"Remove a planning assignment row from u_plano and its plan lines.\"\"\"\r\n        select_query = (\r\n            \"SELECT u_planostamp FROM u_plano WHERE data = ? AND fref = ? AND processo = ?\"\r\n        )\r\n        delete_plan_query = (\r\n            \"DELETE FROM u_plano WHERE data = ? AND fref = ? AND processo = ?\"\r\n        )\r\n        delete_lines_query = (\r\n            \"DELETE FROM u_lplano WHERE u_planostamp = ?\"\r\n        )\r\n        params = (assignment_date, team_code, project_code)\r\n        try:\r\n            with self.connect() as conn:\r\n                cursor = conn.cursor()\r\n                cursor.execute(select_query, params)\r\n                rows = cursor.fetchall() or []\r\n                plan_stamps = []\r\n                for row in rows:\r\n                    stamp = row[0] if row and len(row) else None\r\n                    if stamp:\r\n                        plan_stamps.append(str(stamp).strip())\r\n                cursor.execute(delete_plan_query, params)\r\n                for stamp in plan_stamps:\r\n                    if not stamp:\r\n                        continue\r\n                    cursor.execute(delete_lines_query, (stamp,))\r\n                conn.commit()\r\n        except Exception as exc:\r\n            raise RuntimeError(str(exc)) from exc\r\n"

if old not in text:
    raise SystemExit('target block not found in database.py')

path.write_text(text.replace(old, new, 1))
