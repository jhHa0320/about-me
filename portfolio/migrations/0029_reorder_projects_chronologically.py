"""프로젝트 목록을 다시 시간순으로 정렬합니다.

`order` 필드가 예전 '대표 프로젝트' 강조용으로 4건만 37~40 으로 튀어 있어,
나머지(0~12)와 섞이면 더 이상 시간순으로 읽히지 않았습니다. 실제 `period`
문구를 기준으로 최신순 1위부터 14위까지 다시 매겨 둡니다. `start_date` 는
비어 있는 채로 두어도 되고, 이후 특정 프로젝트를 앞세우고 싶으면 관리자에서
`order` 값을 이 범위보다 높게 주면 됩니다.

pk 로 찾되 제목 일부가 맞는지 확인하고, 어긋나면 건드리지 않습니다.
"""

from django.db import migrations

# pk: (제목 확인용 조각, order) — order 는 높을수록 먼저(최신) 노출됩니다.
ORDER_BY_RECENCY = {
    14: ("SNU AI Challenge", 14),          # 2026.7
    13: ("보안 취약점", 13),                # 2026년 1학기
    11: ("개인 포트폴리오 사이트", 12),      # 2026년 2월 -
    12: ("픽합주", 11),                     # 2025년 12월 -
    10: ("리뷰 감성 분석", 10),              # 2025년 2학기
    9: ("풍력 발전량", 9),                  # 2025년 1학기 - 여름방학
    8: ("게임 이용 통제", 8),                # 2025년 1학기
    7: ("SAS KOREA", 7),                    # 2025년 1학기
    5: ("데이터톤", 6),                     # 2024년 겨울방학
    6: ("제스처", 5),                       # 2024년 2학기
    2: ("빨뚜", 4),                         # 2024년 2학기
    3: ("뉴스 링커", 3),                    # 2024년 2학기
    4: ("전통시장", 2),                     # 2024년 여름방학
    1: ("숭실의 나침반", 1),                 # 2024년 1학기
}


def reorder(apps, schema_editor):
    Project = apps.get_model("portfolio", "Project")

    for pk, (title_fragment, order) in ORDER_BY_RECENCY.items():
        project = Project.objects.filter(pk=pk).first()
        if project is None or title_fragment not in project.title:
            continue    # 다른 환경이라 pk 가 어긋난 경우 — 건드리지 않는다.
        project.order = order
        project.save(update_fields=["order"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0028_backfill_skill_domain"),
    ]

    operations = [
        migrations.RunPython(reorder, noop),
    ]
