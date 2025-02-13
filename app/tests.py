"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".
"""

import json
from datetime import UTC, datetime
from django.test import TestCase
from .models import ShieldModel, ShipModel, WeaponModel, LoadoutModel, CustomUser
from .simulation import Simulation, Contestant, Damage, DamageResult, Hull, Shield, Weapon, Modifier



class TestModels(TestCase):
    """Tests for Application Models."""
    def setUp(self):
        """Prepare a Test User if not already available."""
        self.test_user = CustomUser(username="tester", 
                                    password="passw0rd!",
                                    first_name="Test", 
                                    last_name="User", 
                                    is_staff=False, 
                                    is_active=True, 
                                    date_joined=datetime.now(tz=UTC))
        self.test_user.save()

        """Test Ship Model"""
        with open("./app/test/resources/ships.json", 'r', encoding='utf-8-sig') as file:
            ships: list[dict] = json.load(file)
            for ship in ships:
                ship_model = ShipModel.from_json_object(ship)
                ship_model.save()

                model = ShipModel.objects.get(name=ship["localName"])
                self.assertIsNotNone(model)
                self.assertIsNotNone(model.name)
                self.assertIsNotNone(model.max_weapon_power)
                self.assertGreaterEqual(model.shield_faces, 0)

        """Test Weapon Model"""
        with open("./app/test/resources/weapons.json", 'r', encoding='utf-8-sig') as file:
            for weapon in json.load(file):
                if weapon["data"]["type"] != "WeaponGun" or weapon["data"].get("subType", "") != "Gun":
                    continue
                weapon_model = WeaponModel.from_json_object(weapon)
                weapon_model.save()
                
                self.assertIsNotNone(weapon_model.name)
                
        """Test Shield Model"""
        with open("./app/test/resources/shields.json", 'r', encoding='utf-8-sig') as file:
            for shield in json.load(file):
                shield_model = ShieldModel.from_json_object(shield)
                shield_model.save()

                self.assertIsNotNone(shield_model.name)
                self.assertIsNotNone(shield_model.size)
                self.assertGreater(shield_model.total_hp, 0)
                
        """Test Loadout Model"""
        with open("./app/test/resources/loadouts.json", 'r') as file:
            for loadout in json.load(file):
                loadout_model = LoadoutModel.from_json_object(loadout)
                loadout_model.user = self.test_user
                loadout_model.save()

                self.assertIsNotNone(loadout_model.name)
                self.assertIsNotNone(loadout_model.ship_name)
                self.assertIsNotNone(loadout_model.weapons)
                self.assertIsNotNone(loadout_model.weapons_power_percentage)
                self.assertIsNotNone(loadout_model.shields)
                self.assertIsNotNone(loadout_model.shields_power_percentage)
                self.assertIsNotNone(loadout_model.user)

    def test_modifier(self):
        mod = Modifier("test_mod", 1, 0)
        shield_starting_hp = 100
        shield_current_hp = shield_starting_hp
        max_damage_value = 5

        timer = 0
        while shield_current_hp > 1 and timer <=100:
            timer += 1
            modified_dmg = mod.apply(max_damage_value)
            shield_current_hp -= modified_dmg

            percentage = shield_current_hp / shield_starting_hp
            mod.decrement(percentage)
            
        self.assertLess(mod.current, mod.maximum)
        mod.current = mod.maximum
        self.assertEqual(mod.current, mod.maximum)

    def test_damage(self):
        shot1 = Damage(3, 0, 0)
        shot2 = Damage(0, 7, 0)
        shot3 = Damage(0, 0, 11)

        self.assertEqual(shot1 + shot2, Damage(3,7,0))
        self.assertEqual(shot3 - shot3, Damage())

    def test_damage_result(self):
        dmg_applied = Damage(10, 0, 0)
        dmg_passed = Damage(8, 0, 0)
        result = DamageResult(dmg_applied, dmg_passed)
        self.assertEqual(result.incoming, dmg_applied)
        self.assertEqual(result.passthrough, dmg_passed)

    def test_weapon(self):
        weapon_models = WeaponModel.objects.all()
        for weapon_model in weapon_models:
            weapon = Weapon(weapon_model, time_on_target=1)
            weapon.set_power_percent(1)
            weapon.calculate_saturation(400, 100)

            dmg1_total = Damage()
            self.assertEqual(weapon.is_ready(1), True)
            for i in range(20):
                dmg_output = weapon.fire()
                dmg1_total += dmg_output
            weapon.cooldown()

            dmg2_total = Damage()
            self.assertEqual(weapon.is_ready(2), True)
            for i in range(20):
                dmg_output = weapon.fire()
                dmg2_total += dmg_output
            weapon.cooldown()

            dmg3_total = Damage()
            self.assertEqual(weapon.is_ready(0.5), True)
            for i in range(20):
                dmg_output = weapon.fire()
                dmg3_total += dmg_output
            weapon.cooldown()
            
            if weapon.burst_dps > 0:
                self.assertNotEqual(dmg2_total.total_damage(), dmg3_total.total_damage())
                self.assertEqual(dmg1_total.total_damage(), dmg2_total.total_damage())
            else:
                self.assertNotEqual(weapon.power_percent, 0)

        self.assertIsNotNone(weapon_models)

    def test_shield(self):
        shield_models = ShieldModel.objects.all()
        for shield_model in shield_models:
            shield = Shield([shield_model], 1, 1)
            self.assertEqual(shield.current_hp, shield_model.total_hp)

            initial_hp = shield.current_hp
            incoming_dmg = Damage(0, 10, 0)
            result = shield.apply_damage(incoming_dmg)

            self.assertEqual(shield.max_hp, shield_model.total_hp)
            self.assertNotEqual(shield.current_hp, shield.max_hp)
            self.assertNotEqual(shield.current_hp, initial_hp)
            self.assertEqual(shield.current_hp, initial_hp - result.incoming.energy)

        self.assertIsNotNone(shield_models)

    def test_hull(self):
        ships = ShipModel.objects.all()

        for ship in ships:
            hull = Hull(ship)

            self.assertEqual(hull.scm_speed, ship.scm_speed)
            self.assertGreaterEqual(hull.shield_faces, 0)

    def test_contestant(self):
        loadouts = LoadoutModel.objects.all()
        for loadout in loadouts:
            contestant = Contestant(loadout)
            self.assertTrue(contestant.is_ready(300, 1200, 1))

    def test_simulation(self):
        sim = Simulation()

        loadouts = LoadoutModel.objects.all().filter(user=self.test_user)
        
        [sim.add_contestant(Contestant(loadout)) for loadout in loadouts]


        results = sim.simulate(sim.contestants[1], sim.contestants[0])
        self.assertNotEqual(results.time_to_kill, 0)
        self.assertEqual(int(results.remaining_shield_hp), 
                             int(results.starting_shield_hp - results.total_damage_applied_to_shield.total_damage()))
        self.assertEqual(int(results.remaining_total_hull_hp), 
                            int(results.starting_total_hull_hp - results.total_damage_applied_to_hull.total_damage()))
        self.assertGreaterEqual(results.total_damage_fired.total_damage(), 
                             results.total_damage_applied_to_hull.total_damage() + results.total_damage_applied_to_hull.total_damage())

        all_results = sim.simulate_all()
        [print(r.summary) for r in all_results]

        circle_test1 = sim.calculate_circle_time(60, 200)
        circle_test2 = sim.calculate_circle_time(35, 170)
        test_adv = 1 + (sim.mobility_bonus * (circle_test1 - circle_test2) / 100)
        self.assertEqual(int((test_adv - 1)*100), -17)
