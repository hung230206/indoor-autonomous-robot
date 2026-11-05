"""8-connected A*, octile heuristic, no diagonal corner cutting."""
import heapq
import math


def astar(grid, start, goal):
    if not grid.free(start) or not grid.free(goal):
        return []

    def heuristic(c):
        dx, dy = abs(c[0] - goal[0]), abs(c[1] - goal[1])
        return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)

    heap = [(heuristic(start), 0.0, start)]
    costs, parent = {start: 0.0}, {}
    while heap:
        _, cost, current = heapq.heappop(heap)
        if cost > costs[current] + 1e-9:
            continue
        if current == goal:
            path = [goal]
            while path[-1] != start:
                path.append(parent[path[-1]])
            return path[::-1]
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)):
            nxt = current[0] + dx, current[1] + dy
            if not grid.free(nxt):
                continue
            if dx and dy and (not grid.free((current[0] + dx, current[1])) or
                              not grid.free((current[0], current[1] + dy))):
                continue
            candidate = cost + (math.sqrt(2) if dx and dy else 1)
            if candidate < costs.get(nxt, math.inf) - 1e-9:
                costs[nxt], parent[nxt] = candidate, current
                heapq.heappush(heap, (candidate + heuristic(nxt), candidate, nxt))
    return []
