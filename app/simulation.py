from statistics import mean
from django.conf import settings
from .models import LoadoutModel, ShipModel, ShieldModel, WeaponModel
import math
import json


class Modifier:
    def __init__(self, mod_type:str, maximum:float, minimum:float=None):
        self.mod_type = mod_type
        self.maximum: float = maximum
        self.minimum: float = maximum
        if minimum != None:
            self.minimum = minimum
        self.current: float = self.maximum

    def decrement(self, percentage:float) -> float:
        self.current = max([ self.minimum, self.maximum - ((self.maximum - self.minimum) * (1 - percentage)) ])
        return self.current

    def apply(self, value:float) -> float:
        return max([ 0, value * self.current ])

    def to_json(self):
        output = {
            "mod_type": self.mod_type,
            "maximum": self.maximum,
            "minimum": self.minimum,
            "current": self.current
            }
        
        return output


class Damage:
    def __init__(self, ballistic:float=0, energy:float=0, distortion:float=0):
        self.ballistic:float = ballistic
        self.energy:float = energy
        self.distortion:float = distortion

    def total_damage(self):
        return sum([self.ballistic, self.energy, self.distortion])

    def __sub__(self, other):
        if isinstance(other, Damage):
            return Damage(ballistic=self.ballistic - other.ballistic,
                          energy=self.energy - other.energy,
                          distortion=self.distortion - other.distortion)
        else:
            raise TypeError(f"Unsupported Operand Type: {type(other)}")

    def __add__(self, other):
        if isinstance(other, Damage):
            return Damage(ballistic=self.ballistic + other.ballistic,
                          energy=self.energy + other.energy,
                          distortion=self.distortion + other.distortion)
        else:
            raise TypeError(f"Unsupported Operand Type: {type(other)}")

    def __eq__(self, other):
        if isinstance(other, Damage):
            if self.ballistic == other.ballistic and \
                  self.energy == other.energy and \
                  self.distortion == other.distortion:
                return True
            else:
                return False
        else:
            raise TypeError(f"Unsupported Operand Type: {type(other)}")

    def to_json(self):
        output = {
            "ballistic": self.ballistic,
            "energy": self.energy,
            "distortion": self.distortion,
            "total": self.total_damage()
            }
        
        return output


class DamageResult:
    def __init__(self, incoming: Damage, passthrough: Damage):
        self.incoming = incoming
        self.passthrough = passthrough

    def to_json(self):
        output = {
            "incoming": self.incoming.to_json(),
            "passthrough": self.passthrough.to_json()
            }
        
        return output
        

    
class Hull: 
    def __init__(self, ship:ShipModel):
        self.max_vital_hp:int = ship.vital_hull_hp
        self.max_nonvital_hp:int = ship.total_hp - ship.vital_hull_hp
        self.current_vital_hp:int = self.max_vital_hp
        self.current_nonvital_hp:float = self.max_nonvital_hp
        self.vital_area:str = ship.vital_hull_name
        self.bal_resistance:Modifier = Modifier(settings.BAL, maximum=1 - ship.ballistic_resistance)
        self.eng_resistance:Modifier = Modifier(settings.ENG, maximum=1 - ship.energy_resistance)
        self.dis_resistance:Modifier = Modifier(settings.DIS, maximum=1 - ship.distortion_resistance)
        self.pitch_rate:int = ship.pitch_rate
        self.scm_speed:int = ship.scm_speed
        self.shield_faces:int = ship.shield_faces
        self.visible_area:float = ship.visible_hull_area
        self.visible_vital_area:float = self.visible_area * 0.3
        self.distortion_limit:int = 6000
        self.distortion_level:float = 0

    def apply_damage(self, damage:Damage) -> DamageResult:
        initial_vital_hp: float = self.current_vital_hp
        initial_nonvital_hp: float = self.current_nonvital_hp

        absorbed: Damage = Damage(ballistic=self.bal_resistance.apply(damage.ballistic),
                                  energy=self.eng_resistance.apply(damage.energy),
                                  distortion=self.dis_resistance.apply(damage.distortion))

        passthrough: Damage = Damage() # no damage splitting on hull, until engineering is online

        if initial_nonvital_hp <= 0:
            self.current_vital_hp = initial_vital_hp - absorbed.total_damage()
        else:
            self.current_vital_hp = initial_vital_hp - (absorbed.total_damage() * (self.visible_vital_area/self.visible_area))
            self.current_nonvital_hp = initial_nonvital_hp - ( absorbed.total_damage() * (1 - (self.visible_vital_area/self.visible_area)) )

        self.distortion_level += absorbed.distortion
        return DamageResult(
            incoming=absorbed, 
            passthrough=passthrough)

    def reset(self):
        self.current_vital_hp = self.max_vital_hp
        self.current_nonvital_hp = self.max_nonvital_hp
        self.bal_resistance.current = self.bal_resistance.maximum
        self.eng_resistance.current = self.eng_resistance.maximum
        self.dis_resistance.current = self.dis_resistance.maximum
        self.distortion_level = 0


    def to_json(self):
        output = {
            "max_vital_hp": self.max_vital_hp,
            "max_nonvital_hp": self.max_nonvital_hp,
            "current_vital_hp": self.current_vital_hp,
            "current_nonvital_hp": self.current_nonvital_hp,
            "vital_area": self.vital_area,
            "bal_resistance": self.bal_resistance.to_json(),
            "eng_resistance": self.eng_resistance.to_json(),
            "dis_resistance": self.dis_resistance.to_json(),
            "pitch_rate": self.pitch_rate,
            "scm_speed": self.scm_speed,
            "shield_faces": self.shield_faces,
            "visible_area": self.visible_area,
            "visible_vital_area": self.visible_vital_area,
            "distortion_limit": self.distortion_limit,
            "distortion_level": self.distortion_level
            }
        
        return output

class Shield:
    def __init__(self, shields:list[ShieldModel], faces:int, power_assigned:int):
        if faces == 0:
            self.max_hp:float = 0
        else:
            self.max_hp:float = sum([shield.total_hp for shield in shields]) / faces
        self.current_hp:float = self.max_hp
        self.max_power_slots = sum([shield.max_power_slots for shield in shields])
        self.power_percentage = power_assigned / self.max_power_slots

        self.bal_resistance = Modifier(settings.BAL,
                                        mean([shield.max_ballistic_resistance for shield in shields]),
                                        mean([shield.min_ballistic_resistance for shield in shields]))
                
        self.eng_resistance = Modifier(settings.ENG,
                                        mean([shield.max_energy_resistance for shield in shields]),
                                        mean([shield.min_energy_resistance for shield in shields]))

        self.dis_resistance = Modifier(settings.DIS,
                                        mean([shield.max_distortion_resistance for shield in shields]),
                                        mean([shield.min_distortion_resistance for shield in shields]))

        self.bal_absorption = Modifier(settings.BAL,
                                        mean([shield.max_ballistic_absorption for shield in shields]),
                                        mean([shield.min_ballistic_absorption for shield in shields]))

        self.eng_absorption = Modifier(settings.ENG,
                                        mean([shield.max_energy_absorption for shield in shields]),
                                        mean([shield.min_energy_absorption for shield in shields]))

        self.dis_absorption = Modifier(settings.DIS,
                                        mean([shield.max_distortion_absorption for shield in shields]),
                                        mean([shield.min_distortion_absorption for shield in shields]))

    def is_ready(self) -> bool:
        ready:bool = True
        if not self.power_percentage or self.power_percentage == 0:
            ready = False
        else:
            self.bal_resistance.decrement(self.power_percentage)
            self.eng_resistance.decrement(self.power_percentage)
            self.dis_resistance.decrement(self.power_percentage)
            self.bal_absorption.decrement(self.power_percentage)
            self.eng_absorption.decrement(self.power_percentage)
            self.dis_absorption.decrement(self.power_percentage)

        if self.current_hp == 0 or self.max_hp == 0:
            ready = False
        return ready

    def apply_damage(self, incoming:Damage) -> DamageResult:
        initial_hp: int = self.current_hp
        if initial_hp <= 0:
            return DamageResult(incoming=Damage(), passthrough=incoming)

        absorbed: Damage = Damage(ballistic=self.bal_absorption.apply(incoming.ballistic),
                                  energy=self.eng_absorption.apply(incoming.energy),
                                  distortion=self.dis_absorption.apply(incoming.distortion) )
        applied: Damage = Damage(ballistic=self.bal_resistance.apply(absorbed.ballistic),
                                 energy=self.eng_resistance.apply(absorbed.energy),
                                 distortion=self.dis_resistance.apply(absorbed.distortion) )
        
        passthrough: Damage = incoming - absorbed
        self.current_hp = initial_hp - applied.total_damage()

        percentage = self.current_hp / self.max_hp
        self.bal_absorption.decrement(percentage)
        self.eng_absorption.decrement(percentage)
        self.dis_absorption.decrement(percentage)
        self.bal_resistance.decrement(percentage)
        self.eng_resistance.decrement(percentage)
        self.dis_resistance.decrement(percentage)
        
        return DamageResult(incoming=applied, 
                            passthrough=passthrough)

    def reset(self):
        self.current_hp = self.max_hp
        self.bal_resistance.current = self.bal_resistance.maximum
        self.bal_absorption.current = self.bal_absorption.maximum
        self.eng_resistance.current = self.eng_resistance.maximum
        self.eng_absorption.current = self.eng_absorption.maximum
        self.dis_resistance.current = self.dis_resistance.maximum
        self.dis_absorption.current = self.dis_absorption.maximum
        self.is_ready()

    def to_json(self):
        output = {
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "max_power_slots": self.max_power_slots,
            "power_percentage": self.power_percentage,
            "bal_resistance": self.bal_resistance.to_json(),
            "eng_resistance": self.eng_resistance.to_json(),
            "dis_resistance": self.dis_resistance.to_json(),
            "bal_absorption": self.bal_absorption.to_json(),
            "eng_absorption": self.eng_absorption.to_json(),
            "dis_absorption": self.dis_absorption.to_json(),
            "is_ready": self.is_ready()
            }
        
        return output

class Weapon:
    def __init__(self, weapon:WeaponModel, time_on_target:float=1):
        self.dmg_type = weapon.damage_type
        self.time_on_target:float = max([0, min([time_on_target, 1]) ])
        self.burst_dps:float = weapon.burst_dps
        self.max_burst_length:float = float(weapon.burst_duration) if weapon.burst_duration else 0
        self.burst_length:float = self.max_burst_length * self.time_on_target
        self.burst_cooldown:float = float(weapon.burst_cooldown) if weapon.burst_cooldown else 0
        self.runtime:float = float(weapon.total_runtime) if weapon.total_runtime else settings.MAX
        self.spread:float = float(weapon.spread) if weapon.spread else 0
        self.projectile_speed:int = int(weapon.projectile_speed) if weapon.projectile_speed else 0
        self.ready_to_fire:bool = False
        self.burst_timer:int = 0
        self.cooldown_timer:int = 0
        self.firing_timer:int = 0
        self.power_percent:float = 0

    def set_power_percent(self, power_percent:float=None, power_slots_available:int=None, power_slots_assigned:int=None) -> None:
        if power_percent:
            self.power_percent = sorted([0, power_percent, 1])[1]
        elif power_slots_assigned and power_slots_available:
            self.power_percent = sorted([0, power_slots_assigned / power_slots_available, 1])
        else:
            self.power_percent = 1

        self.burst_length = self.max_burst_length * self.power_percent
        

    def is_ready(self, adv:float=1) -> bool:
        ready:bool = True

        if not self.dmg_type:
            ready = False
        if not self.spread:
            self.spread = 0
        if not self.power_percent:
            self.power_percent = 1

        if not self.time_on_target:
            self.time_on_target = max([0, min([1 * adv, 1]) ]) 
        else:
            self.time_on_target = max([0, min([self.time_on_target * adv, 1]) ])


        self.ready_to_fire = ready

        return ready
    
    def calculate_saturation(self, distance:int, target_size:float):
        self.spread_radius = math.tan(self.spread/2) * distance
        self.target_saturation_percent = sorted([0, 100*(target_size**2)/(self.spread_radius**2), 1])[1]
        self.target_vital_percent = sorted([0, ((target_size * .6)**2)/(target_size**2), 1])[1]

    def fire(self) -> Damage:
        damage_output = Damage()

        if self.ready_to_fire:
            self.firing_timer += 1
            self.burst_timer += 1
            
            if self.dmg_type == settings.BAL:
                damage_output.ballistic = self.burst_dps * self.time_on_target

            elif self.dmg_type == settings.ENG:
                damage_output.energy = self.burst_dps * self.time_on_target

            elif self.dmg_type == settings.DIS:
                damage_output.distortion = self.burst_dps * self.time_on_target

            if self.burst_timer >= self.burst_length:
                self.burst_timer = 0
                self.cooldown_timer = 0
                self.ready_to_fire = False

            if self.firing_timer >= self.runtime:
                self.ready_to_fire = False

        else:
            if self.firing_timer < self.runtime:
                self.cooldown_timer += 1
                if self.cooldown_timer >= self.burst_cooldown:
                    self.burst_timer = 0
                    self.cooldown_timer = 0
                    self.ready_to_fire = True
                else:
                    self.burst_timer = 0
                    self.ready_to_fire = False
            else:
                self.ready_to_fire = False

        return damage_output

    def cooldown(self):
        self.ready_to_fire = True
        self.burst_timer = 0
        self.cooldown_timer = 0
        self.firing_timer = 0

    def to_json(self):
        output = {
            "dmg_type": self.dmg_type,
            "burst_dps": self.burst_dps,
            "max_burst_length": self.max_burst_length,
            "burst_length": self.burst_length,
            "burst_cooldown": self.burst_cooldown,
            "runtime": self.runtime,
            "spread": self.spread,
            "projectile_speed": self.projectile_speed,
            "time_on_target": self.time_on_target,
            "ready_to_fire": self.ready_to_fire,
            "burst_timer": self.burst_timer,
            "cooldown_timer": self.cooldown_timer,
            "firing_timer": self.firing_timer,
            "power_percent": self.power_percent
            }

        return output


class Contestant:
    def __init__(self, loadout:LoadoutModel=None):
        self.name:str = "Uninitialized"
        self.weapon_power:float = 0
        self.pilot_tot:float = 0.75
        self.turret_tot:float = 0.95
        self.distance:float = 400
        self.mobility_multiplier:float = 1
        self.ship:Hull
        self.shields:Shield
        self.weapons:list[Weapon] = []
        self.operators:dict = {}
        self.weapon_power:float = 0
        self.shield_power:float = 0

        if loadout:
            self.name = loadout.name
            self.weapon_power = loadout.weapons_power_percentage
            self.shield_power = loadout.shields_power_percentage

            ship_model = ShipModel.objects.get(name=loadout.ship_name)
            if ship_model:
                self.ship: Hull = Hull(ship_model)
                
            shields_list = [ShieldModel.objects.get(name=shield) for shield in loadout.shields]
            self.shields = Shield(shields_list, faces=self.ship.shield_faces, power_assigned=loadout.shields_power_percentage)

            [self.operators.update({operator: []}) for operator in loadout.weapons.keys()]

            for operator in self.operators.keys():
                weapons_list = loadout.weapons.get(operator, [])

                weapons = []
                for weapon_name in weapons_list:
                    w = WeaponModel.objects.get(name=weapon_name)
                    if operator.lower() == "pilot":
                        time_on_target = self.pilot_tot
                    else:
                        time_on_target = self.turret_tot
                 
                    weapon = Weapon(w, time_on_target)
                    weapon.set_power_percent(power_percent=loadout.weapons_power_percentage)

                    weapons.append(weapon)
                self.operators[operator] = weapons
                self.weapons.extend(weapons)

    def is_ready(self, dist:int, size:float, adv:float) -> bool:
        ready:bool = True

        if len(self.weapons) == 0:
            ready = False
        for weapon in self.weapons:
            weapon.calculate_saturation(dist, size)
            if not weapon.is_ready(adv):
                ready = False
        if not self.shields or not self.shields.is_ready():
            ready = False
        if not self.ship:
            ready = False

        return ready

    def fire_weapons(self) -> Damage:
        total = Damage()

        for weapon in self.weapons:
            total += weapon.fire()

        return total

    def apply_damage(self, incoming_dmg:Damage) -> set[DamageResult]:
        shield_result = self.shields.apply_damage(incoming_dmg)
        passthrough_dmg = shield_result.passthrough
        hull_result = self.ship.apply_damage(passthrough_dmg)

        result = (shield_result, hull_result)
        return result

    def reset(self):
        self.shields.reset()
        self.ship.reset()
        for weapon in self.weapons:
            weapon.cooldown()

    def to_json(self):
        output = {
            "name": self.name,
            "weapon_power": self.weapon_power,
            "pilot_tot": self.pilot_tot,
            "turret_tot": self.turret_tot,
            "distance": self.distance,
            "mobility_multiplier": self.mobility_multiplier,
            "ship": self.ship.to_json(),
            "shields": self.shields.to_json(),
            "weapons": [weapon.to_json() for weapon in self.weapons],
            "weapon_power": self.weapon_power,
            "shield_power": self.shield_power
            }
        
        return output

class Simulation:
    def __init__(self):
        self.contestants: list[Contestant] = []
        self.estimation: bool = True
        self.distance:int = 400
        self.mobility_bonus:float = 4
        self.max_simulation_time: int = 999
        self.simulation_results: list = []

    class SimulationResult:
        def __init__(self):
            self.attacker:Contestant
            self.defender:Contestant
            self.time_to_kill:int
            self.time_limit:int
            self.mobility_advantage:float
            self.distance:int
            self.estimation:bool
            self.total_damage_fired:Damage = Damage()
            self.total_damage_applied_to_hull:Damage = Damage()
            self.total_damage_applied_to_shield:Damage = Damage()
            self.remaining_shield_hp:int
            self.remaining_vital_hull_hp:int
            self.remaining_total_hull_hp:int
            self.starting_total_hull_hp:int
            self.starting_vital_hull_hp:int
            self.starting_shield_hp:int
        
        @property
        def summary(self) -> str:
            return f"""{self.attacker.name.upper()} ATTACKING {self.defender.name.upper()} 
    Engagement Distance: {self.distance} | Mobility Advantage: {int((self.mobility_advantage - 1) * 100)}% | Time to Kill - {self.time_to_kill if (self.time_to_kill < 1000) else 'No Kill (Out of Ammo)'} 
            """

        def to_json(self):
            output = {
                "attacker": self.attacker.to_json(),
                "defender": self.defender.to_json(),
                "time_to_kill": self.time_to_kill,
                "time_limit": self.time_limit,
                "mobility_advantage": self.mobility_advantage,
                "distance": self.distance,
                "estimation": self.estimation,
                "total_damage_fired": self.total_damage_fired.to_json(),
                "total_damage_applied_to_hull": self.total_damage_applied_to_hull.to_json(),
                "total_damage_applied_to_shield": self.total_damage_applied_to_shield.to_json(),
                "remaining_shield_hp": self.remaining_shield_hp,
                "remaining_vital_hull_hp": self.remaining_vital_hull_hp,
                "remaining_total_hull_hp": self.remaining_total_hull_hp,
                "starting_vital_hull_hp": self.starting_vital_hull_hp,
                "starting_total_hull_hp": self.starting_total_hull_hp,
                "starting_shield_hp": self.starting_shield_hp
                }
            
            return output

    def to_json(self):
        output = {
            "contestants": [contestant.to_json() for contestant in self.contestants],
            "estimation": self.estimation,
            "distance": self.distance,
            "mobility_bonus": self.mobility_bonus,
            "max_simulation_time": self.max_simulation_time,
            "simulation_results": [result.to_json() for result in self.simulation_results]
            }
        
        return output

    def add_contestant(self, contestant) -> bool:
        if isinstance(contestant, Contestant):
            self.contestants.append(contestant)
            return True
        else:
            return False
        
    def calculate_circle_time(self, pitch_rate:float, speed:float) -> float:
        if not self.estimation:
            return 10.0

        pitch_rate_rads = math.radians(pitch_rate)

        if pitch_rate_rads == 0 or speed == 0:
            return float('inf')

        radius = speed/pitch_rate_rads
        circumference = 2*math.pi*radius
        time = circumference / speed
        return time

    def reset(self):
        for contestant in self.contestants:
            contestant.reset()

    def simulate(self, target:Contestant, attacker:Contestant) -> SimulationResult:
        result:Simulation.SimulationResult = Simulation.SimulationResult()
        result.attacker = attacker
        result.defender = target
        result.estimation = self.estimation
        result.distance = self.distance
        result.time_limit = self.max_simulation_time

        #calculate mobility advantage
        adv: float = 1
        if self.estimation:
            adv = ( self.mobility_bonus * ( 
                        self.calculate_circle_time(
                            target.ship.pitch_rate, target.ship.scm_speed
                    ) - self.calculate_circle_time(
                            attacker.ship.pitch_rate, attacker.ship.scm_speed)
                   ) / 100) + 1

            if adv == float("inf"):
                adv = 1
        attacker.mobility_multiplier = adv
        result.mobility_advantage = adv

        if not attacker.is_ready(self.distance, target.ship.visible_area, adv):
            raise "Attacker not Ready!"
        if not target.is_ready(self.distance, attacker.ship.visible_area, adv):
            raise "Defender not Ready!"

        timer:int = 0
        while timer <= self.max_simulation_time and \
                target.ship.current_vital_hp >= 0 and \
                target.ship.distortion_level <= target.ship.distortion_limit:

            timer += 1
            damage_output: Damage = attacker.fire_weapons()

            shield_dmg_result, hull_dmg_result = target.apply_damage(damage_output)

            result.total_damage_fired += damage_output
            result.total_damage_applied_to_shield += shield_dmg_result.incoming
            result.total_damage_applied_to_hull += hull_dmg_result.incoming

        
        result.time_to_kill = timer
        result.remaining_shield_hp = target.shields.current_hp
        result.remaining_vital_hull_hp = target.ship.current_vital_hp
        result.remaining_total_hull_hp = target.ship.current_nonvital_hp + target.ship.current_vital_hp
        result.starting_vital_hull_hp = target.ship.max_vital_hp
        result.starting_total_hull_hp = target.ship.max_nonvital_hp + target.ship.max_vital_hp
        result.starting_shield_hp = target.shields.max_hp

        return result

    def simulate_all(self) -> list[SimulationResult]:
        results = []
        self.reset()
        for attacker in self.contestants:
            for defender in self.contestants:
                if attacker != defender:
                    results.append(self.simulate(defender, attacker))
                    self.reset()
        return results