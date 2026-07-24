.PHONY: test-coverage sonar-up sonar-scan sonar-check sonar-down

test-coverage:
	uv run --isolated --extra dev pytest

sonar-up:
	docker compose -f docker-compose.sonar.yml up -d sonarqube

sonar-scan:
	docker compose -f docker-compose.sonar.yml run --rm scanner

sonar-check: test-coverage sonar-scan

sonar-down:
	docker compose -f docker-compose.sonar.yml down
