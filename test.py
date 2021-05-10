from yfantasy_api.api import YahooFantasyApi
import csv
import sys
TEAMS = ['Andrew', 'Chay', 'Fabian', 'Hogan', 'Joe', 'Kenzie', 'Kyle', 'Mason', 'Richard', 'Ryan', 'Travis', 'Trevor']
INACTIVE_TEAMS = ['Brad', 'Geoff', 'Reid', 'Ryan G.']

MASTER_MAPPING = {
    'Fabian Mayer': 'Fabian',
    'Mike': 'Hogan',
    'Prime Time': 'Kenzie',
    'ryan': 'Ryan',
    'Trevor Wong': 'Trevor',
    'Ryan': 'Ryan G.'
}

GAMES_LIST = [
    {'year': 2015, 'game_code': 352, 'league_id': 503},
    {'year': 2016, 'game_code': 363, 'league_id': 1787, 'mappings': {'Geoff': 'Brad'}},
    {'year': 2017, 'game_code': 376, 'league_id': 175},
    {'year': 2018, 'game_code': 386, 'league_id': 1994},
    {'year': 2019, 'game_code': 396, 'league_id': 5194},
    {'year': 2020, 'game_code': 403, 'league_id': 17457}
]


def add_dict(parent, child):
    for k in child:
        if k not in parent:
            parent[k] = child[k]
        else:
            for k2 in child[k]:
                if k2 not in parent[k]:
                    parent[k][k2] = child[k][k2]
                else:
                    parent[k][k2] += child[k][k2]


def get_head_to_head(game_code, league_id, year, mappings={}):
    print(f'Getting head-to-head records for {year}...')
    head_to_head = {}
    mappings = mappings | MASTER_MAPPING
    api = YahooFantasyApi(league_id, game_code)
    game_weeks = ','.join([g.week for g in api.game().game_weeks().get().game_weeks])
    matchups = api.league().scoreboard(week=game_weeks).get().matchups
    for matchup in matchups:
        if matchup.is_playoffs:
            continue
        winning_team = [t for t in matchup.teams if t.team.info.team_key == matchup.winner_team_key][0]
        losing_team = [t for t in matchup.teams if t.team.info.team_key != matchup.winner_team_key][0]
        winning_mgr = winning_team.team.info.managers[0].nickname
        losing_mgr = losing_team.team.info.managers[0].nickname

        winning_mgr = winning_mgr if winning_mgr not in mappings else mappings[winning_mgr]
        losing_mgr = losing_mgr if losing_mgr not in mappings else mappings[losing_mgr]

        if winning_mgr in INACTIVE_TEAMS or losing_mgr in INACTIVE_TEAMS:
            continue

        if winning_mgr not in head_to_head:
            head_to_head[winning_mgr] = {}
        if losing_mgr not in head_to_head[winning_mgr]:
            head_to_head[winning_mgr][losing_mgr] = 0
        head_to_head[winning_mgr][losing_mgr] += 1
    return head_to_head


def get_career_head_to_head():
    career_head_to_head = {}
    for game in GAMES_LIST:
        add_dict(career_head_to_head, get_head_to_head(**game))
    return career_head_to_head


def get_latest_head_to_head():
    return get_head_to_head(**GAMES_LIST[-1])


def output_data(name, head_to_head, teams):
    data = []
    for team in teams:
        matchup_data = [team]
        total_wins = total_losses = 0
        for opp in teams:
            if team == opp:
                matchup_data.append('XXX')
                continue

            wins = losses = 0
            if opp in head_to_head[team]:
                wins += head_to_head[team][opp]
                total_wins += wins
            if team in head_to_head[opp]:
                losses += head_to_head[opp][team]
                total_losses += losses
            matchup_data.append(f'{wins}-{losses}')
        data.append(matchup_data + [f'{total_wins}-{total_losses}', total_wins + total_losses])

    with open(f'h2h-{name}.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['XXX'] + teams + ['Record', 'Total'])
        writer.writerows(data)

    teams = ['XXX'] + teams + ['Record', 'Total']
    print(teams)
    for d in data:
        print(d)


def get_statistics(game_code, league_id, year, mappings={}):
    print(f'Getting statistics for {year}...')
    mappings = mappings | MASTER_MAPPING
    api = YahooFantasyApi(league_id, game_code)
    data = {}
    standings = api.league().standings().get().standings
    for team in standings:
        manager = team.info.managers[0].nickname
        manager = manager if manager not in mappings else mappings[manager]
        games_played = team.wins + team.losses + team.ties
        data[team.info.team_key] = {
            'name': manager,
            'gp': games_played,
            'w': team.wins,
            'l': team.losses,
            't': team.ties,
            'p': (2 * team.wins) + team.ties,
            #'w%': team.percentage,
            'pf': round(team.points_for, 2),
            'pa': round(team.points_against, 2),
            'pd': round(team.points_for - team.points_against, 2),
            #'pf/g': round(team.points_for / games_played, 2),
            #'pa/g': round(team.points_against / games_played, 2),
            #'pd/g': round((team.points_for - team.points_against) / games_played, 2),
            'moves': 0,
            'trades': 0
        }
    transactions = api.league().transactions().get().transactions
    for transaction in transactions:
        if transaction.type == 'trade':
            if transaction.status != 'successful':
                continue
            data[transaction.tradee_team_key]['trades'] += 1
            data[transaction.trader_team_key]['trades'] += 1
        elif transaction.type == 'drop':
            continue
            data[transaction.source_team_key]['moves'] += 1
        else:
            data[transaction.destination_team_key]['moves'] += 1
    return data


def get_career_statistics():
    career_statistics = {}
    for game in GAMES_LIST:
        season_statistics = get_statistics(**game)
        for _, data in season_statistics.items():
            name = data.pop('name')
            if name not in career_statistics:
                career_statistics[name] = data
            else:
                for k, v in data.items():
                    career_statistics[name][k] += v
            season_pf_g = data['pf'] / data['gp']
            current_max = career_statistics[name].get('max_pf')
            if not current_max or season_pf_g > current_max:
                career_statistics[name]['max_pf'] = season_pf_g
                career_statistics[name]['max_year'] = game['year']
            current_min = career_statistics[name].get('min_pf')
            if not current_min or season_pf_g < current_min:
                career_statistics[name]['min_pf'] = season_pf_g
                career_statistics[name]['min_year'] = game['year']

            points_perc = data['p'] / (data['gp'] * 2)
            best_pp = career_statistics[name].get('best_pp')
            if not best_pp or points_perc > best_pp:
                career_statistics[name]['best_pp'] = points_perc
                career_statistics[name]['best_pp_year'] = game['year']
                career_statistics[name]['best_record'] = f"{data['w']}-{data['l']}"
            worst_pp = career_statistics[name].get('worst_pp')
            if not best_pp or points_perc < worst_pp:
                career_statistics[name]['worst_pp'] = points_perc
                career_statistics[name]['worst_pp_year'] = game['year']
                career_statistics[name]['worst_record'] = f"{data['w']}-{data['l']}"
    return career_statistics

if __name__ == '__main__':
    champs = {}
    for team, defences, streak in [('Trevor', 0, 'Week 1 (2015) - Week 2 (2015)'), ('Joe', 1, 'Week 2 (2015) - Week 4 (2015)'), ('Ryan', 0, 'Week 4 (2015) - Week 5 (2015)'), ('Travis', 0, 'Week 5 (2015) - Week 6 (2015)'), ('Joe', 0, 'Week 6 (2015) - Week 7 (2015)'), ('Brad', 2, 'Week 7 (2015) - Week 10 (2015)'), ('Mason', 5, 'Week 10 (2015) - Week 16 (2015)'), ('Travis', 5, 'Week 16 (2015) - Week 22 (2015)'), ('Brad', 2, 'Week 22 (2015) - Week 3 (2016)'), ('Fabian', 0, 'Week 3 (2016) - Week 4 (2016)'), ('Richard', 0, 'Week 4 (2016) - Week 5 (2016)'), ('Ryan', 0, 'Week 5 (2016) - Week 6 (2016)'), ('Travis', 0, 'Week 6 (2016) - Week 7 (2016)'), ('Richard', 3, 'Week 7 (2016) - Week 11 (2016)'), ('Fabian', 0, 'Week 11 (2016) - Week 12 (2016)'), ('Trevor', 0, 'Week 12 (2016) - Week 13 (2016)'), ('Richard', 3, 'Week 13 (2016) - Week 17 (2016)'), ('Mason', 0, 'Week 17 (2016) - Week 18 (2016)'), ('Ryan', 1, 'Week 18 (2016) - Week 20 (2016)'), ('Travis', 2, 'Week 20 (2016) - Week 2 (2017)'), ('Fabian', 0, 'Week 2 (2017) - Week 3 (2017)'), ('Richard', 0, 'Week 3 (2017) - Week 4 (2017)'), ('Trevor', 2, 'Week 4 (2017) - Week 7 (2017)'), ('Joe', 2, 'Week 7 (2017) - Week 10 (2017)'), ('Mason', 2, 'Week 10 (2017) - Week 13 (2017)'), ('Ryan', 1, 'Week 13 (2017) - Week 15 (2017)'), ('Hogan', 0, 'Week 15 (2017) - Week 16 (2017)'), ('Reid', 0, 'Week 16 (2017) - Week 17 (2017)'), ('Joe', 4, 'Week 17 (2017) - Week 1 (2018)'), ('Mason', 0, 'Week 1 (2018) - Week 2 (2018)'), ('Ryan', 0, 'Week 2 (2018) - Week 3 (2018)'), ('Richard', 2, 'Week 3 (2018) - Week 6 (2018)'), ('Fabian', 1, 'Week 6 (2018) - Week 8 (2018)'), ('Ryan', 2, 'Week 8 (2018) - Week 11 (2018)'), ('Mason', 0, 'Week 11 (2018) - Week 12 (2018)'), ('Chay', 2, 'Week 12 (2018) - Week 15 (2018)'), ('Ryan', 1, 'Week 15 (2018) - Week 17 (2018)'), ('Fabian', 1, 'Week 17 (2018) - Week 19 (2018)'), ('Travis', 0, 'Week 19 (2018) - Week 20 (2018)'), ('Trevor', 2, 'Week 20 (2018) - Week 2 (2019)'), ('Richard', 2, 'Week 2 (2019) - Week 5 (2019)'), ('Mason', 2, 'Week 5 (2019) - Week 8 (2019)'), ('Fabian', 0, 'Week 8 (2019) - Week 9 (2019)'), ('Ryan', 0, 'Week 9 (2019) - Week 10 (2019)'), ('Trevor', 1, 'Week 10 (2019) - Week 12 (2019)'), ('Travis', 0, 'Week 12 (2019) - Week 13 (2019)'), ('Hogan', 1, 'Week 13 (2019) - Week 15 (2019)'), ('Fabian', 1, 'Week 15 (2019) - Week 17 (2019)'), ('Mason', 0, 'Week 17 (2019) - Week 18 (2019)'), ('Trevor', 8, 'Week 18 (2019) - Week 6 (2020)'), ('Kyle', 6, 'Week 6 (2020) - Current')]:
        print(team, streak, f'({defences} defences)')
        if team not in champs:
            champs[team] = {'wins': 0, 'defences': 0, 'held': 0}
        champs[team]['wins'] += 1
        champs[team]['defences'] += defences
        champs[team]['held'] += (defences + 1)
    print()
    total_held = 0
    for team, data in champs.items():
        print(team, data)
        total_held += data['held']
    print(total_held)
    #exit()

    losses = {}
    data = []
    champ_year = champ_week = 0
    champion = None
    defences = 0
    for game in GAMES_LIST:
        mappings = game.get('mappings', {}) | MASTER_MAPPING
        api = YahooFantasyApi(game['league_id'], game['game_code'])
        year = game['year']

        teams = api.league().teams().get().teams
        league_teams = {mappings.get(team.info.managers[0].nickname, team.info.managers[0].nickname): team.info.team_key for team in teams}
        #print(league_teams)
        game_weeks = ','.join([g.week for g in api.game().game_weeks().get().game_weeks])
        matchups = api.league().scoreboard(week=game_weeks).get().matchups
        weekly_matchups = {}
        for matchup in matchups:
            if matchup.week not in weekly_matchups:
                weekly_matchups[matchup.week] = []
            weekly_matchups[matchup.week].append(matchup)

        for week, matchups in weekly_matchups.items():
            if not champion:
                teams = [team for teams in [matchup.teams for matchup in matchups] for team in teams]
                manager = sorted(teams, key=lambda x: x.team_points, reverse=True)[0].team.info.managers[0]
                champion = mappings.get(manager.nickname, manager.nickname)
                champ_year = year
                champ_week = week
                continue

            for matchup in matchups:
                if matchup.is_playoffs:
                    continue

                winning_team = [t.team for t in matchup.teams if t.team.info.team_key == matchup.winner_team_key][0]
                losing_team = [t.team for t in matchup.teams if t.team.info.team_key != matchup.winner_team_key][0]
                winning_mgr = mappings.get(winning_team.info.managers[0].nickname, winning_team.info.managers[0].nickname)
                losing_mgr = mappings.get(losing_team.info.managers[0].nickname, losing_team.info.managers[0].nickname)

                if winning_team.info.team_key == league_teams[champion]:
                    if losing_mgr not in losses:
                        losses[losing_mgr] = 0
                    losses[losing_mgr] += 1
                    defences += 1
                elif losing_team.info.team_key == league_teams[champion]:
                    if losing_mgr not in losses:
                        losses[losing_mgr] = 0
                    losses[losing_mgr] += 1
                    data.append((champion, defences, f'Week {champ_week} ({champ_year}) - Week {week} ({year})'))
                    champion = mappings.get(winning_team.info.managers[0].nickname, winning_team.info.managers[0].nickname)
                    champ_week = week
                    champ_year = year
                    defences = 0
                else:
                    continue
    data.append((champion, defences, f'Week {champ_week} ({champ_year}) - Current'))
    print(data)     
    print(losses)   
            
            









    exit()

    #career_statistics = get_career_statistics()
    #writer = csv.writer(sys.stdout)
    #writer.writerow(['Team'] + list(career_statistics['Travis'].keys()))
    #for k, v in career_statistics.items():
    #    writer.writerow([k] + list(v.values()))
    #exit()


    career_head_to_head = get_career_head_to_head()
    output_data('career', career_head_to_head, TEAMS)

    latest_head_to_head = get_latest_head_to_head()
    output_data('latest', latest_head_to_head, TEAMS)
