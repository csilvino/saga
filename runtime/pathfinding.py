"""
Módulo de Pathfinding A* para a Saga Engine.
"""
import arcade
from typing import List, Tuple, Optional

def find_path(
    start_position: Tuple[float, float],
    end_position: Tuple[float, float],
    walkable_grid: arcade.AStarBarrierList,
    grid_size: int = 64 # Tamanho de cada célula do grid
) -> Optional[List[Tuple[float, float]]]:
    """
    Encontra um caminho entre dois pontos usando o algoritmo A*.

    Args:
        start_position: A posição inicial (x, y).
        end_position: A posição final (x, y).
        walkable_grid: Uma AStarBarrierList que define as áreas caminháveis/não caminháveis.
        grid_size: O tamanho de cada célula do grid para o pathfinding.

    Returns:
        Uma lista de tuplas (x, y) representando o caminho, ou None se nenhum caminho for encontrado.
    """
    # Converte as coordenadas de pixel para coordenadas de grid
    start_grid_x = int(start_position[0] // grid_size)
    start_grid_y = int(start_position[1] // grid_size)
    end_grid_x = int(end_position[0] // grid_size)
    end_grid_y = int(end_position[1] // grid_size)

    # Garante que as posições de início e fim estão dentro dos limites do grid
    if not (0 <= start_grid_x < walkable_grid.grid_width and 0 <= start_grid_y < walkable_grid.grid_height):
        print(f"Erro: Posição inicial ({start_grid_x}, {start_grid_y}) fora dos limites do grid.")
        return None
    if not (0 <= end_grid_x < walkable_grid.grid_width and 0 <= end_grid_y < walkable_grid.grid_height):
        print(f"Erro: Posição final ({end_grid_x}, {end_grid_y}) fora dos limites do grid.")
        return None

    # Calcula o caminho
    path_grid = arcade.astar_calculate_path(
        start_grid_x, start_grid_y,
        end_grid_x, end_grid_y,
        walkable_grid,
        diagonal_movement=False # Por enquanto, movimento não-diagonal
    )

    if path_grid:
        # Converte o caminho de volta para coordenadas de pixel (centro da célula)
        path_pixels = []
        for grid_x, grid_y in path_grid:
            center_x = grid_x * grid_size + grid_size / 2
            center_y = grid_y * grid_size + grid_size / 2
            path_pixels.append((center_x, center_y))
        return path_pixels
    return None

if __name__ == '__main__':
    # Exemplo de uso e teste rápido
    # Cria um grid 10x10
    grid_width = 10
    grid_height = 10
    grid_size = 64 # Pixels por célula

    # Cria uma AStarBarrierList vazia (tudo caminhável)
    barrier_list = arcade.AStarBarrierList(
        grid_width, grid_height, grid_size, []
    )

    # Adiciona algumas barreiras (células não caminháveis)
    # barrier_list.add_barrier(3, 3)
    # barrier_list.add_barrier(3, 4)
    # barrier_list.add_barrier(3, 5)

    start = (grid_size / 2, grid_size / 2) # Centro da célula (0,0)
    end = (grid_width * grid_size - grid_size / 2, grid_height * grid_size - grid_size / 2) # Centro da célula (9,9)

    print(f"Procurando caminho de {start} para {end}")
    path = find_path(start, end, barrier_list, grid_size)

    if path:
        print("Caminho encontrado:")
        for p in path:
            print(f"  {p}")
    else:
        print("Nenhum caminho encontrado.")
